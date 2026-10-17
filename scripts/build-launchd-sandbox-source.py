#!/usr/bin/env python3
"""Build complete launchd with live Sandbox queries in a private runtime."""
from pathlib import Path
from datetime import datetime, timezone
import fcntl, hashlib, json, re, runpy, shutil, subprocess

root = Path(__file__).resolve().parent.parent
darling = root / 'vendor/darling'
profile = runpy.run_path(str(root / 'scripts/sandbox-policy-vm-server-profile.py'))['profile']()
config = json.loads((root / 'config/launchd-source-build.json').read_text())
digest = lambda n: hashlib.sha256((root / n).read_bytes()).hexdigest()
assert subprocess.check_output(['git', '-C', str(darling), 'rev-parse', 'HEAD'], text=True).strip() == config['darling_commit']
for path, revision in config['header_repositories'].items():
    assert subprocess.check_output(['git', '-C', str(root / path), 'rev-parse', 'HEAD'], text=True).strip() == revision
assert digest(config['original_launchd']) == config['original_launchd_sha256']
source = darling / 'src/launchd/src'
sdk = darling / 'Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
apple = root / 'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
resource = Path(subprocess.check_output(['clang-19', '-print-resource-dir'], text=True).strip())
build = root / 'runtime/launchd-sandbox-source'
build.mkdir(exist_ok=True)
mig = root / 'runtime/darlingserver-source-build/build-mig'
definitions = ['-DDARLING', '-DPRIVATE', '-Dxpc_domain_server=job_server', '-DPLATFORM_MacOSX', '-D__DARWIN_UNIX03']
includes = [source, darling / 'src/launchd/liblaunch', build, darling / 'src/external/libxpc/include', sdk / 'usr/include', resource / 'include']
common = ['-target', 'x86_64-apple-macos11', '-isysroot', str(sdk), '-nostdinc',
          *definitions, *['-I' + str(p) for p in includes]]
cmake = (source / 'CMakeLists.txt').read_text()
commands = []
log = root / 'logs/launchd-sandbox-source-build.log'
with log.open('w') as output:
    def run(command):
        commands.append(command)
        subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, check=True)
    for name in re.findall(r'^mig\((\w+)\.defs\)', cmake, re.M):
        run([str(mig), '-arch', 'x86_64', *common,
             '-user', str(build / (name + 'User.c')), '-header', str(build / (name + '.h')),
             '-server', str(build / (name + 'Server.c')), '-sheader', str(build / (name + 'Server.h')),
             str(source / (name + '.defs'))])
    section = re.search(r'set\(launchd_sources\s+(.*?)\n\)', cmake, re.S)[1]
    sources = []
    for line in section.splitlines():
        line = line.strip()
        if line.startswith('#') or not line.endswith('.c'): continue
        sources.append(build / line.rsplit('/', 1)[-1] if '${CMAKE_CURRENT_BINARY_DIR}/' in line else source / line)
    assert len(sources) == 16
    objects = []
    for path in sources:
        obj = build / (path.stem + '.o'); objects.append(str(obj))
        run(['clang-19', *common, '-F', str(sdk / 'System/Library/Frameworks'),
             '-idirafter', str(apple / 'usr/include'), '-include', str(sdk / 'usr/include/sys/fileport.h'),
             '-fblocks', '-O2', '-Wno-deprecated-declarations', '-Wno-incompatible-pointer-types',
             '-Wno-implicit-function-declaration', '-Wno-int-conversion',
             '-Wno-nullability-completeness', '-Wno-macro-redefined', '-c', str(path), '-o', str(obj)])
    guest = root / 'runtime/rootfs/usr/libexec/darling'
    pending = build / 'launchd.pending'
    run(['ld64.lld-19', '-arch', 'x86_64', '-platform_version', 'macos', '11', '11',
         '-syslibroot', str(guest), '-L', str(guest / 'usr/lib'), '-lbsm.0', '-lSystem', *objects, '-o', str(pending)])
    output_binary = build / 'launchd'; pending.replace(output_binary)
    macros = subprocess.check_output(['clang-19', *common, '-E', '-dM', '-x', 'c', str(source / 'config.h')], text=True)
    assert '#define HAVE_SANDBOX 1' in macros
    (build / 'config.macros').write_text(macros)
symbols = subprocess.check_output(['llvm-nm', '-an', str(output_binary)], text=True)
assert re.search(r'\bU _sandbox_check_by_audit_token$', symbols, re.M)
(build / 'launchd.symbols').write_text(symbols)
selected = {key: dict(item) for key, item in profile['source_runtime'].items()}
base = (root / selected['LINUXCODE_LIBDYLD']['path']).parent / 'darling-root'
variant = build / 'darling-root'
with (root / 'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    staging = build / 'darling-root.pending'
    if staging.exists(): shutil.rmtree(staging)
    subprocess.run(['cp', '-a', '--reflink=auto', str(base), str(staging)], check=True)
    shutil.copy2(output_binary, staging / 'sbin/launchd')
    for key, item in selected.items():
        target = build / Path(item['path']).name
        if key != 'LINUXCODE_LAUNCHD':
            assert digest(item['path']) == item['sha256']
            shutil.copy2(root / item['path'], target)
        item.update(path=str(target.relative_to(root)), sha256=digest(target.relative_to(root)))
    if variant.exists(): shutil.rmtree(variant)
    staging.replace(variant)
paths = [*sources, source / 'config.h', source / 'CMakeLists.txt', source / 'runtime.h',
         darling / 'src/sandbox/sandbox.h']
report = dict(checked_at=datetime.now(timezone.utc).isoformat(), full_launchd_source_build=True,
              complete_source_files=len(sources), commands=commands,
              binary=str(output_binary.relative_to(root)), binary_sha256=digest(output_binary.relative_to(root)),
              log=str(log.relative_to(root)), log_sha256=digest(log.relative_to(root)),
              source_files={str(p.relative_to(root)): digest(p.relative_to(root)) for p in paths},
              previous_source_runtime=profile['source_runtime'], source_runtime=selected,
              variant_root=str(variant.relative_to(root)), config_macros=str((build / 'config.macros').relative_to(root)),
              config_macros_sha256=digest((build / 'config.macros').relative_to(root)),
              symbols=str((build / 'launchd.symbols').relative_to(root)),
              symbols_sha256=digest((build / 'launchd.symbols').relative_to(root)),
              sandbox_queries_enabled=True, queries_use_Mach_caller_audit_token=True,
              nonzero_query_results_deny=True, runtime_execution_verified=False,
              XPC_domain_lookup_exemption_still_present=True,
              profile_application_implemented=False, full_xcode_build_ready=False, default_entry_promoted=False)
(root / 'artifacts/launchd-sandbox-source-build.json').write_text(json.dumps(report, indent=2) + '\n')
print('Built 16-source launchd with enabled Sandbox audit queries in an independent runtime')
