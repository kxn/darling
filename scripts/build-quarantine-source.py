#!/usr/bin/env python3
"""Build complete Darling libquarantine, including source responsibility APIs."""
from pathlib import Path
import fcntl,hashlib,json,re,shutil,subprocess
root=Path(__file__).resolve().parent.parent
source=root/'vendor/darling/src/quarantine'
build=root/'runtime/quarantine-source';build.mkdir(exist_ok=True)
config=json.loads((root/'config/quarantine-source-build.json').read_text())
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for relative,commit in config['source_repositories'].items():
    if subprocess.check_output(['git','-C',str(root/relative),'rev-parse','HEAD'],text=True).strip()!=commit:
        raise ValueError('Changed quarantine source/header revision: '+relative)
baseline=root/config['baseline']
if digest(baseline)!=config['baseline_sha256']:raise ValueError('Changed baseline quarantine')
sdk=root/'vendor/darling/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
resource=Path(subprocess.check_output(['clang-19','-print-resource-dir'],text=True).strip())
text=(source/'CMakeLists.txt').read_text()
section=re.search(r'set\(quarantine_sources\s+([^)]*)\)',text)[1]
sources=[source/p for p in section.split()]
if len(sources)!=2 or any(not p.is_file() for p in sources):raise ValueError('Incomplete quarantine source list')
objects=[]
for path in sources:
    obj=build/(path.stem+'.o');objects.append(obj)
    subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-nostdinc',
        '-I',str(source/'include'),'-isystem',str(sdk/'usr/include'),'-isystem',str(resource/'include'),
        '-DDARLING','-DDARWIN','-DPLATFORM_MacOSX','-DTARGET_OS_MAC=1',
        '-D_DARWIN_C_SOURCE','-D__DARWIN_UNIX03','-fPIC','-O2',
        '-c',str(path),'-o',str(obj)],check=True)
guest=root/'runtime/rootfs/usr/libexec/darling'
output=build/'libquarantine.dylib';pending=output.with_name(output.name+'.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11',
    '-syslibroot',str(guest),'-L',str(guest/'usr/lib/system'),
    '-install_name','/usr/lib/system/libquarantine.dylib','-compatibility_version','1.0.0',
    '-lsystem_c','-ldyld','-lsystem_malloc','-lsystem_kernel','-lsystem_pthread',
    *[str(p) for p in objects],'-o',str(pending)],check=True)
def exports(path):
    listing=subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(path)],text=True)
    return set(re.findall(r'^0x[\da-fA-F]+\s+(\S+)',listing,re.M))
missing=exports(baseline)-exports(pending)
if missing:raise ValueError('Missing old quarantine exports: '+repr(sorted(missing)))
pending.replace(output)
base=root/'runtime/libsystem-kernel-source/darling-root'
kernel=root/'runtime/libsystem-kernel-source/libsystem_kernel.dylib'
if digest(base/'usr/lib/system/libsystem_kernel.dylib')!=digest(kernel):raise ValueError('Stale source kernel variant')
variant=build/'darling-root'
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    new_root=build/'darling-root.pending';previous=build/'darling-root.previous'
    for owned in (new_root,previous):
        if owned.exists():shutil.rmtree(owned)
    subprocess.run(['cp','-a','--reflink=auto',str(base),str(new_root)],check=True)
    shutil.copy2(output,new_root/'usr/lib/system/libquarantine.dylib')
    if variant.exists():variant.replace(previous)
    new_root.replace(variant)
    if previous.exists():shutil.rmtree(previous)
report=dict(installed=False,full_darling_rebuild=False,full_quarantine_source_build=True,
    runtime_execution_verified=False,source_configuration=config,
    source_files={str(p.relative_to(root)):digest(p) for p in [*sources,source/'CMakeLists.txt',source/'include/responsibility.h']},
    original_exports_preserved=len(exports(baseline)),source_exports=len(exports(output)),
    library_sha256=digest(output),source_kernel_sha256=digest(kernel),variant_root=str(variant.relative_to(root)),
    scope='Selected Quarantine spawn responsibility state; no macOS TCC enforcement, entitlements, malware policy or other MAC policy support claim.')
(root/'artifacts/quarantine-source.json').write_text(json.dumps(report,indent=2)+'\n')
print('Built complete source libquarantine:',output)
