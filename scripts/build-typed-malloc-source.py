#!/usr/bin/env python3
"""Compile the complete upstream legacy-allocator typed entry-point layer."""
from pathlib import Path
import fcntl, hashlib, json, runpy, subprocess
root = Path(__file__).resolve().parent.parent
digest = lambda p: hashlib.sha256((root / p).read_bytes()).hexdigest()
base = root / 'runtime/os-log-simple-source/libraries/libSystem.B.dylib'
old = json.loads((root / 'artifacts/os-log-simple-source-stage.json').read_text())
assert digest(base.relative_to(root)) == old['library_sha256']
source = 'vendor/darling/src/external/libmalloc/src/malloc_type_stubs.c'
upstream = root / 'vendor/apple-libmalloc'
assert subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip() == 'c49dafa25f1efe8607701ae6014a663ad2ee437f'
assert (root / source).read_bytes() == (upstream / 'src/malloc_type_stubs.c').read_bytes()
build = root / 'runtime/typed-malloc-source'
libraries = build / 'libraries'
libraries.mkdir(parents=True, exist_ok=True)
sdk = root / 'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
guest = root / 'runtime/rootfs/usr/libexec/darling'
obj = build / 'loader.o'
subprocess.run(['clang-19', '-target', 'x86_64-apple-macos11', '-isysroot', str(sdk), '-O2', '-c',
    str(root / source), '-o', str(obj)], check=True)
helper = libraries / 'libDarlingTypedMalloc.dylib'
pending = helper.with_suffix('.pending')
subprocess.run(['ld64.lld-19', '-dylib', '-arch', 'x86_64', '-platform_version', 'macos', '11', '11',
    '-syslibroot', str(guest), '-L', str(guest / 'usr/lib'), '-lSystem',
    '-install_name', '/usr/lib/libDarlingTypedMalloc.dylib', str(obj), '-o', str(pending)], check=True)
api = runpy.run_path(str(root / 'scripts/macho-named-reexport.py'))
names = ['malloc', 'calloc', 'free', 'realloc', 'valloc', 'aligned_alloc', 'posix_memalign',
    'zone_malloc', 'zone_calloc', 'zone_free', 'zone_realloc', 'zone_valloc', 'zone_memalign']
payload, changes = api['add'](base.read_bytes(), '/usr/lib/libDarlingTypedMalloc.dylib', ['_malloc_type_' + name for name in names])
with (root / 'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    pending.replace(helper)
    target = libraries / 'libSystem.B.dylib'
    temporary = target.with_suffix('.pending'); temporary.write_bytes(payload); temporary.replace(target)
report = dict(installed=False, runtime_execution_verified=False,
    base=str(base.relative_to(root)), base_sha256=digest(base.relative_to(root)),
    library=str(target.relative_to(root)), library_sha256=digest(target.relative_to(root)),
    helper=str(helper.relative_to(root)), helper_sha256=digest(helper.relative_to(root)),
    upstream_commit='c49dafa25f1efe8607701ae6014a663ad2ee437f', upstream_source_bytes_unchanged=True,
    typed_allocation_isolation_implemented=False, full_libmalloc_source_build=False,
    export_changes=changes, source=source, source_sha256=digest(source),
    scope='All 13 unchanged Apple fallback entry points call the real existing allocator. Typed zone isolation is absent; this is not the modern malloc_type.c/xzone implementation.',
    full_xcode_build_ready=False, signing_ready=False)
(root / 'artifacts/typed-malloc-source-stage.json').write_text(json.dumps(report, indent=2) + '\n')
print('Built 13 unchanged Apple fallback allocation entry points over the real allocator')
