#!/usr/bin/env python3
"""Build the complete Darling trace library into a private replacement provider."""
from pathlib import Path
import argparse, fcntl, hashlib, json, re, subprocess

root = Path(__file__).resolve().parent.parent
repo = root / 'vendor/darling/src/external/libtrace'
commit = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
assert commit == '8cf07f02b15f7dca6436882a03678fff0392eaf6'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir',default='runtime/libtrace-source')
parser.add_argument('--report',default='artifacts/libtrace-source-build.json')
args=parser.parse_args()
build = root / args.output_dir
libraries = build / 'libraries'
libraries.mkdir(parents=True, exist_ok=True)
sdk = root / 'vendor/darling/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
apple = root / 'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
resource = Path(subprocess.check_output(['clang-19', '-print-resource-dir'], text=True).strip())
sources = re.findall(r'\S+\.(?:c|m)', (repo / 'CMakeLists.txt').read_text().split('set(system_trace_sources', 1)[1].split(')', 1)[0])
assert len(sources) in (8,9), sources
objects = []
for index, relative in enumerate(sources):
    source = repo / relative
    obj = build / (str(index) + '-' + source.stem + '.o')
    print('Compile', relative, flush=True)
    subprocess.run(['clang-19', '-target', 'x86_64-apple-macos11', '-isysroot', str(sdk),
        '-nostdinc', '-I' + str(repo / 'libsbuf'), '-I' + str(repo / 'include'),
        '-I' + str(root / 'vendor/darling/src/duct/include'),
        '-isystem', str(sdk / 'usr/include'), '-isystem', str(resource / 'include'),
        '-idirafter', str(apple / 'usr/include'), '-F', str(sdk / 'System/Library/Frameworks'),
        '-DDARLING', '-DPLATFORM_MacOSX', '-D__DARWIN_UNIX03', '-D_LIBC_NO_FEATURE_VERIFICATION',
        '-DOS_LOG_PRIVACY=1', '-fPIC', '-fblocks', '-O2', '-Wno-deprecated-declarations',
        '-Wno-nullability-completeness', '-Wno-macro-redefined', '-Wno-availability',
        '-c', str(source), '-o', str(obj)], check=True)
    objects.append(obj)
guest = root / 'runtime/rootfs/usr/libexec/darling'
output = libraries / 'libTrace.dylib'
pending = output.with_suffix('.pending')
guestpath = lambda p: '/Volumes/SystemRoot/workspace/' + str(p.relative_to(root))
guestbase = '/Volumes/SystemRoot/usr/libexec/darling'
subprocess.run(['timeout', '-k', '5', '60', str(root / 'bin/darling'), 'shell',
    '/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/ld-classic',
    '-dylib', '-arch', 'x86_64', '-platform_version', 'macos', '11.0', '11.0',
    '-install_name', '/usr/lib/libTrace.dylib', '-compatibility_version', '1.0', '-current_version', '1.0',
    '-syslibroot', guestbase, '-L', guestbase + '/usr/lib/system', '-L', guestbase + '/usr/lib',
    *['-l' + name for name in ['system_platform', 'system_kernel', 'system_c', 'system_malloc', 'system_asl',
        'system_duct', 'dispatch', 'dyld', 'system_blocks','system_pthread','unwind']], '-upward_library', guestbase + '/usr/lib/libobjc.A.dylib',
    *[guestpath(p) for p in objects], '-o', guestpath(pending)], cwd=root, check=True)
exports = lambda p: set(re.findall(r'^(?:0x[\da-fA-F]+|\[re-export\])\s+(\S+)',
    subprocess.check_output(['llvm-objdump-19', '--macho', '--exports-trie', str(p)], text=True), re.M))
old = exports(guest / 'usr/lib/libTrace.dylib')
new = exports(pending)
assert not old - new, sorted(old - new)
assert '_os_log_decode_buffer' in new
assert '_os_log_compare_enablement' in new
if len(sources)==9:assert '_os_log_set_hook' in new
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    pending.replace(output)
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
report = dict(installed=False, full_libtrace_source_build=True, complete_source_files=len(sources), source_commit=commit,
    source_files={s: digest(repo / s) for s in sources}, library=str(output.relative_to(root)), library_sha256=digest(output),
    original_exports_preserved=len(old), source_exports=len(new),
    source_headers={str(p.relative_to(repo)):digest(p) for p in [repo/'include/os/log_private.h',repo/'include/os/log.h',repo/'libsystem_trace/os_log_s.h',repo/'CMakeLists.txt']},
    source_scope='Original trace/object/ASL path with checked encoded-buffer parsing, corrected annotation cursor and NUL capacity; native log enablement rank comparator. Other existing trace/activity/formatter stubs remain unsupported.',
    runtime_execution_verified=False, full_xcode_build_ready=False, signing_ready=False)
report_path=root/args.report
temporary=report_path.with_suffix('.pending');temporary.write_text(json.dumps(report, indent=2) + '\n');temporary.replace(report_path)
print('Built isolated complete source libTrace provider')
