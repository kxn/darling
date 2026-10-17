#!/usr/bin/env python3
"""Build the Apple simple-log source port without replacing the platform runtime."""
from pathlib import Path
import fcntl, hashlib, json, runpy, subprocess
root = Path(__file__).resolve().parent.parent
digest = lambda p: hashlib.sha256((root / p).read_bytes()).hexdigest()
repo = root / 'vendor/darling/src/external/libplatform'
upstream = root / 'vendor/apple-libplatform'
assert subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip() == '2512ffd8bb5c6caff3c8ea83331ab8a0adc820c3'
original = (upstream / 'src/simple/log_simple.c').read_text()
ported = (repo / 'src/simple/log_simple.c').read_text()
normalized = ported.replace('#ifdef DARLING\n#include "log_simple_darling.h"\n#endif\n', '').replace('#ifndef DARLING\n#include <pthread/private.h>\n#endif', '#include <pthread/private.h>')
normalized = normalized.replace('#ifdef DARLING\n\t_darling_os_log_simple_diagnostic(payload);\n#endif\n', '')
assert normalized == original.replace('\x01', '')
for relative in ['private/os/log_simple_private.h', 'private/os/log_simple_private_impl.h']:
    assert (repo / relative).read_bytes() == (upstream / relative).read_bytes()
build = root / 'runtime/os-log-simple-source'; libraries = build / 'libraries'; libraries.mkdir(parents=True, exist_ok=True)
sdk = root / 'vendor/darling/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
apple = root / 'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
objects = []; inputs = {}
for relative in ['src/simple/log_simple.c', 'src/simple/log_simple_transport.c']:
    obj = build / (Path(relative).stem + '.o'); objects.append(obj)
    deps = obj.with_suffix('.d')
    subprocess.run(['clang-19', '-target', 'x86_64-apple-macos11', '-isysroot', str(sdk),
        '-I', str(repo / 'private'), '-I', str(root / 'vendor/darling/src/external/dyld/gen/usr/local/include'),
        '-I', str(root / 'vendor/darling/src/external/xnu/osfmk'), '-idirafter', str(apple / 'usr/include'),
        '-DDARLING', '-DPRIVATE', '-DPLATFORM_MacOSX', '-D__DARWIN_UNIX03', '-D_LIBC_NO_FEATURE_VERIFICATION',
        '-O2', '-Wno-availability', '-Wno-unguarded-availability-new', '-Wno-macro-redefined',
        '-MD', '-MF', str(deps), '-c', str(repo / relative), '-o', str(obj)], check=True)
    # Workspace paths have no spaces; the compiler's dependency list includes SDK headers.
    for path in deps.read_text().replace('\\\n', ' ').split(':', 1)[1].split():
        file = Path(path)
        key = str(file.relative_to(root)) if file.is_relative_to(root) else str(file)
        inputs[key] = hashlib.sha256(file.read_bytes()).hexdigest()
guest = root / 'runtime/rootfs/usr/libexec/darling'
helper = libraries / 'libDarlingSimpleLog.dylib'; pending = helper.with_suffix('.pending')
subprocess.run(['ld64.lld-19', '-dylib', '-arch', 'x86_64', '-platform_version', 'macos', '11', '11',
    '-syslibroot', str(guest), '-L', str(guest / 'usr/lib'), '-lSystem', '-lproc',
    '-install_name', '/usr/lib/libDarlingSimpleLog.dylib', *map(str, objects), '-o', str(pending)], check=True)
base = root / 'runtime/rootless-datavault-export/libraries/libSystem.B.dylib'
previous = json.loads((root / 'artifacts/rootless-datavault-export-stage.json').read_text())
assert digest(str(base.relative_to(root))) == previous['library_sha256']
api = runpy.run_path(str(root / 'scripts/macho-named-reexport.py'))
names = ['__os_log_simple', '___os_log_simple_offset', '__os_log_simple_shim', '__os_log_simple_send',
    '__os_log_simple_parse', '__os_log_simple_reinit_4launchd', '_os_log_simple_now', '_os_log_simple_type_from_asl']
payload, changes = api['add'](base.read_bytes(), '/usr/lib/libDarlingSimpleLog.dylib', names)
with (root / 'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    pending.replace(helper)
    target = libraries / 'libSystem.B.dylib'; temporary = target.with_suffix('.pending')
    temporary.write_bytes(payload); temporary.replace(target)
report = dict(installed=False, full_libplatform_source_build=False, full_simple_log_source_port=True,
    upstream_commit='2512ffd8bb5c6caff3c8ea83331ab8a0adc820c3', source_function_bodies_preserved_except_optional_diagnostic_call=True,
    compile_inputs=inputs, base=str(base.relative_to(root)), base_sha256=digest(str(base.relative_to(root))),
    library=str(target.relative_to(root)), library_sha256=digest(str(target.relative_to(root))),
    helper=str(helper.relative_to(root)), helper_sha256=digest(str(helper.relative_to(root))), export_changes=changes,
    source_files={str((repo / p).relative_to(root)): digest(str((repo / p).relative_to(root))) for p in
        ['src/simple/log_simple.c', 'src/simple/log_simple_transport.c', 'src/simple/log_simple_darling.h',
         'private/os/log_simple_private.h', 'private/os/log_simple_private_impl.h', 'CMakeLists.txt']},
    runtime_execution_verified=False, persistent_logd_delivery_verified=False,
    early_boot_signal_and_fork_safety_verified=False, full_xcode_build_ready=False, signing_ready=False)
(root / 'artifacts/os-log-simple-source-stage.json').write_text(json.dumps(report, indent=2) + '\n')
print('Built complete upstream simple-log code and actual Unix datagram transport')
