#!/usr/bin/env python3
"""Expose the matched native public/private sysdir state machine."""
from pathlib import Path
import fcntl, hashlib, json, runpy, subprocess
root = Path(__file__).resolve().parent.parent
digest = lambda p: hashlib.sha256((root / p).read_bytes()).hexdigest()
base = root / 'runtime/sandbox-container-source/libraries/libSystem.B.dylib'
old = json.loads((root / 'artifacts/sandbox-container-source-stage.json').read_text())
assert digest(base.relative_to(root)) == old['library_sha256']
native = root / 'runtime/foundation-native-library-stage/libDarlingNativeDirHelper.dylib'
reconstruction = json.loads((root / 'runtime/rebuilt-dirhelper-native/reconstruction.json').read_text())
assert digest(native.relative_to(root)) == reconstruction['staged_image_sha256']
build = root / 'runtime/sysdir-native-export'
libraries = build / 'libraries'
libraries.mkdir(parents=True, exist_ok=True)
sdk = root / 'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
guest = root / 'runtime/rootfs/usr/libexec/darling'
obj = build / 'loader.o'
subprocess.run(['clang-19', '-target', 'x86_64-apple-macos11', '-isysroot', str(sdk), '-O2', '-c',
    str(root / 'scripts/sysdir-native-loader.c'), '-o', str(obj)], check=True)
helper = libraries / 'libDarlingSysdir.dylib'
pending = helper.with_suffix('.pending')
subprocess.run(['ld64.lld-19', '-dylib', '-arch', 'x86_64', '-platform_version', 'macos', '11', '11',
    '-syslibroot', str(guest), '-L', str(guest / 'usr/lib'), '-lSystem',
    '-install_name', '/usr/lib/libDarlingSysdir.dylib', str(obj), '-o', str(pending)], check=True)
api = runpy.run_path(str(root / 'scripts/macho-named-reexport.py'))
payload, changes = api['add'](base.read_bytes(), '/usr/lib/libDarlingSysdir.dylib', ['_sysdir_start_search_path_enumeration', '_sysdir_start_search_path_enumeration_private', '_sysdir_get_next_search_path_enumeration'])
with (root / 'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    pending.replace(helper)
    target = libraries / 'libSystem.B.dylib'
    temporary = target.with_suffix('.pending'); temporary.write_bytes(payload); temporary.replace(target)
report = dict(installed=False, runtime_execution_verified=False,
    base=str(base.relative_to(root)), base_sha256=digest(base.relative_to(root)),
    library=str(target.relative_to(root)), library_sha256=digest(target.relative_to(root)),
    helper=str(helper.relative_to(root)), helper_sha256=digest(helper.relative_to(root)),
    original_provider=str(native.relative_to(root)), original_provider_sha256=digest(native.relative_to(root)),
    export_changes=changes, source='scripts/sysdir-native-loader.c', source_sha256=digest('scripts/sysdir-native-loader.c'),
    scope='Three typed deferred entries call the same unchanged original sysdir provider; states are never decoded by the old Darling implementation.',
    full_xcode_build_ready=False, signing_ready=False)
(root / 'artifacts/sysdir-native-export-stage.json').write_text(json.dumps(report, indent=2) + '\n')
print('Staged the three matching native sysdir entries through named libSystem exports')
