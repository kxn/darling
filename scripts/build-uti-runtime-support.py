#!/usr/bin/env python3
"""Build the upstream async backtrace entry and stage native feature flags."""
from pathlib import Path
import fcntl, hashlib, json, re, runpy, struct, subprocess

root = Path(__file__).resolve().parent.parent
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
build = root / 'runtime/uti-runtime-support'
libraries = build / 'libraries'
libraries.mkdir(parents=True, exist_ok=True)
reference = root / 'runtime/backtrace-async-reference.c'
assert digest(reference) == '78e87e9f7e7e03288f4b396cb7182b9f52bdb1f93bde08f2885de2c6a572092e'
def function(text):
    start = text.index('size_t backtrace_async(')
    return text[start:text.index('\n}', start) + 2]
assert function(reference.read_text()) == function((root / 'scripts/backtrace-async.c').read_text())
config = json.loads((root / 'config/foundation-libc-compat.json').read_text())
for relative, sha in config['files'].items():
    assert digest(root / relative) == sha, relative
stack = (root / 'runtime/thread-stack-pcs-reference.c').read_text()
changes = {
    '#include <mach-o/dyld_priv.h>': '#include <stdbool.h>\n#include <stddef.h>\n#include <stdint.h>',
    '#include <pthread/private.h>': '#define __PTK_FRAMEWORK_SWIFT_KEY3 103\n#define _pthread_getspecific_direct pthread_getspecific',
    '#include "stack_logging.h"': '',
    '\t_dyld_stack_range(&dyldstackbot, &dyldstacktop);': '\t/* Pinned legacy dyld has no alternate dyld stack. */',
}
for before, after in changes.items():
    assert stack.count(before) == 1
    stack = stack.replace(before, after)
(build / 'thread-stack.c').write_text(stack)
sdk = root / config['sdk']
objects = []
for source in [root / 'scripts/backtrace-async.c', build / 'thread-stack.c']:
    obj = build / (source.stem + '.o')
    subprocess.run(['clang-19', '-target', 'x86_64-apple-macos11', '-isysroot', str(sdk),
        '-O2', '-fno-omit-frame-pointer',
        *(['-fvisibility=hidden'] if source.stem == 'thread-stack' else []),
        '-c', str(source), '-o', str(obj)], check=True)
    objects.append(str(obj))
guest = root / 'runtime/rootfs/usr/libexec/darling'
helper = libraries / 'libDarlingBacktraceAsync.dylib'
pending = helper.with_suffix('.pending')
# Export exactly the new entry; the original frame walker stays local.
subprocess.run(['ld64.lld-19', '-dylib', '-arch', 'x86_64', '-platform_version', 'macos', '11', '11',
    '-syslibroot', str(guest), '-L', str(guest / 'usr/lib'), '-lSystem',
    '-install_name', '/usr/lib/libDarlingBacktraceAsync.dylib',
    '-exported_symbol', '_backtrace_async', *objects, '-o', str(pending)], check=True)
# The public entry needs default visibility even with the internal walker hidden.
exports = subprocess.check_output(['llvm-objdump-19', '--macho', '--exports-trie', str(pending)], text=True)
assert '_backtrace_async' in exports, exports
assert re.findall(r'^0x[0-9A-Fa-f]+\s+(\S+)', exports, re.M) == ['_backtrace_async']
bridge_obj = build / 'featureflags-native-loader.o'
subprocess.run(['clang-19', '-target', 'x86_64-apple-macos11', '-isysroot', str(sdk),
    '-O2', '-c', str(root / 'scripts/featureflags-native-loader.c'), '-o', str(bridge_obj)], check=True)
bridge = libraries / 'libDarlingFeatureFlags.dylib'
bridge_pending = bridge.with_suffix('.pending')
subprocess.run(['ld64.lld-19', '-dylib', '-arch', 'x86_64', '-platform_version', 'macos', '11', '11',
    '-syslibroot', str(guest), '-L', str(guest / 'usr/lib'), '-lSystem',
    '-install_name', '/usr/lib/libDarlingFeatureFlags.dylib',
    '-exported_symbol', '__os_feature_enabled_impl', '-exported_symbol', '__os_feature_enabled_simple_impl',
    str(bridge_obj), '-o', str(bridge_pending)], check=True)
bridge_exports = subprocess.check_output(['llvm-objdump-19', '--macho', '--exports-trie', str(bridge_pending)], text=True)
assert set(re.findall(r'^0x[0-9A-Fa-f]+\s+(\S+)', bridge_exports, re.M)) == {'__os_feature_enabled_impl', '__os_feature_enabled_simple_impl'}
for path in [pending, bridge_pending]:
    data = path.read_bytes()
    at = 32
    dependencies = []
    for _ in range(struct.unpack_from('<I', data, 16)[0]):
        cmd, size = struct.unpack_from('<II', data, at)
        if cmd in (0xc, 0x80000018, 0x8000001f, 0x80000023):
            start = at + struct.unpack_from('<I', data, at + 8)[0]
            dependencies.append(data[start:data.index(0, start)].decode())
        if cmd == 0x19:
            for i in range(struct.unpack_from('<I', data, at + 64)[0]):
                section = at + 72 + 80 * i
                assert data[section:section + 16].split(b'\0')[0] != b'__mod_init_func' or not struct.unpack_from('<Q', data, section + 40)[0]
        at += size
    assert dependencies == ['/usr/lib/libSystem.B.dylib'], dependencies
native = root / 'runtime/rebuilt-system-featureflags-native'
native_report = json.loads((native / 'reconstruction.json').read_text())
feature = native / 'libsystem_featureflags.dylib'
assert digest(feature) == native_report['staged_image_sha256']
assert native_report['exports'] == 2 and not native_report['backend_call_overrides']
assert set(native_report['redirected_imports']) == {'_malloc_type_malloc', '_xpc_dictionary_create_empty'}
base = root / 'runtime/pthread-yield-export/libraries/libSystem.B.dylib'
proof = json.loads((root / 'artifacts/pthread-yield-export-stage.json').read_text())
assert digest(base) == proof['staged_library_sha256']
api = runpy.run_path(str(root / 'scripts/macho-named-reexport.py'))
payload, backtrace_change = api['add'](base.read_bytes(), '/usr/lib/libDarlingBacktraceAsync.dylib', ['_backtrace_async'])
payload, feature_change = api['add'](payload, '/usr/lib/libDarlingFeatureFlags.dylib', ['__os_feature_enabled_impl', '__os_feature_enabled_simple_impl'])
with (root / 'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    pending.replace(helper)
    bridge_pending.replace(bridge)
    for name, data in [('libsystem_featureflags.dylib', feature.read_bytes()), ('libSystem.B.dylib', payload)]:
        path = libraries / name
        temporary = path.with_suffix('.pending')
        temporary.write_bytes(data)
        temporary.replace(path)
report = dict(installed=False, runtime_execution_verified=False,
    source_commit=config['thread_stack_source_commit'], upstream_backtrace_body_unchanged=True,
    source_files={p: digest(root / p) for p in ['scripts/backtrace-async.c', 'runtime/backtrace-async-reference.c', 'runtime/thread-stack-pcs-reference.c', 'scripts/build-uti-runtime-support.py', 'scripts/featureflags-native-loader.c']},
    libraries={str(p.relative_to(root)): digest(p) for p in sorted(libraries.glob('*.dylib'))},
    base=str(base.relative_to(root)), base_sha256=digest(base),
    export_changes=[backtrace_change, feature_change], native_featureflags_reconstruction=native_report,
    source_helpers_have_no_initializers_and_only_libSystem_dependency=True,
    scope='Original feature-flag implementation and upstream backtrace_async over the pinned x86_64 frame walker. No alternate-stack or remote-thread guarantees.',
    full_xcode_build_ready=False, signing_ready=False)
(root / 'artifacts/uti-runtime-support-stage.json').write_text(json.dumps(report, indent=2) + '\n')
print('Staged upstream backtrace_async and original system feature flags; runtime unverified')
