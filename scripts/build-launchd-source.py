#!/usr/bin/env python3
"""Build the complete Darling launchd source into an uninstalled variant."""
from pathlib import Path
import fcntl,hashlib,json,re,shutil,subprocess

root=Path(__file__).resolve().parent.parent
darling=root/'vendor/darling'
expected='60ba801decee7a00782f74f6be4c8ffb013f79ff'
config=json.loads((root/'config/launchd-source-build.json').read_text())
for relative,commit in config['header_repositories'].items():
    if subprocess.check_output(['git','-C',str(root/relative),'rev-parse','HEAD'],text=True).strip()!=commit:
        raise ValueError('Changed launchd header source: '+relative)
if hashlib.sha256((root/config['original_launchd']).read_bytes()).hexdigest()!=config['original_launchd_sha256']:
    raise ValueError('Changed packaged launchd')
if subprocess.check_output(['git','-C',str(darling),'rev-parse','HEAD'],text=True).strip()!=expected:
    raise ValueError('Changed Darling source revision')
source=darling/'src/launchd/src';liblaunch=darling/'src/launchd/liblaunch'
build=root/'runtime/launchd-source';build.mkdir(exist_ok=True)
sdk=darling/'Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
resource=Path(subprocess.check_output(['clang-19','-print-resource-dir'],text=True).strip())
apple=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
mig=root/'runtime/darlingserver-source-build/build-mig'
if not mig.exists():raise ValueError('Build the standalone darlingserver MIG tools first')
definitions=['-DDARLING','-DPRIVATE','-Dxpc_domain_server=job_server','-DPLATFORM_MacOSX','-D__DARWIN_UNIX03']
includes=[source,liblaunch,build,darling/'src/external/libxpc/include',sdk/'usr/include',resource/'include']
cmake=(source/'CMakeLists.txt').read_text()
for name in re.findall(r'^mig\((\w+)\.defs\)',cmake,re.M):
    print('MIG',name,flush=True)
    subprocess.run([str(mig),'-arch','x86_64','-target','x86_64-apple-macos11',
        '-isysroot',str(sdk),'-nostdinc',*definitions,*['-I'+str(p) for p in includes],
        '-user',str(build/(name+'User.c')),'-header',str(build/(name+'.h')),
        '-server',str(build/(name+'Server.c')),'-sheader',str(build/(name+'Server.h')),
        str(source/(name+'.defs'))],check=True)
section=re.search(r'set\(launchd_sources\s+(.*?)\n\)',cmake,re.S).group(1)
sources=[]
for line in section.splitlines():
    line=line.strip()
    if line.startswith('#') or not line.endswith('.c'):continue
    if '${CMAKE_CURRENT_BINARY_DIR}/' in line:sources.append(build/line.rsplit('/',1)[-1])
    else:sources.append(source/line)
objects=[]
for path in sources:
    obj=build/(path.stem+'.o');objects.append(str(obj))
    print('Compile',path.name,flush=True)
    subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),
        '-nostdinc',*['-I'+str(p) for p in includes],*definitions,
        '-F',str(sdk/'System/Library/Frameworks'),
        '-idirafter',str(apple/'usr/include'),
        '-include',str(sdk/'usr/include/sys/fileport.h'),'-fblocks','-O2',
        '-Wno-deprecated-declarations','-Wno-incompatible-pointer-types',
        '-Wno-implicit-function-declaration','-Wno-int-conversion',
        '-Wno-nullability-completeness','-Wno-macro-redefined',
        '-c',str(path),'-o',str(obj)],check=True)
guest=root/'runtime/rootfs/usr/libexec/darling';output=build/'launchd'
pending=output.with_name('launchd.pending')
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11',
    '-syslibroot',str(guest),'-L',str(guest/'usr/lib'),'-lbsm.0','-lSystem',
    *objects,'-o',str(pending)],check=True)
pending.replace(output)
variant=build/'darling-root'
base=root/'runtime/libxpc-source/darling-root'
if not base.exists():raise ValueError('Build the complete source libxpc runtime first')
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    pending_root=build/'darling-root.pending';previous=build/'darling-root.previous'
    for owned in (pending_root,previous):
        if owned.exists():shutil.rmtree(owned)
    subprocess.run(['cp','-a','--reflink=auto',str(base),str(pending_root)],check=True)
    subprocess.run(['cp','-p','--reflink=auto',str(output),str(pending_root/'sbin/launchd')],check=True)
    if variant.exists():variant.replace(previous)
    pending_root.replace(variant)
    if previous.exists():shutil.rmtree(previous)
modified=subprocess.check_output(['git','-C',str(darling),'diff','--name-only','--','src/launchd'],text=True).splitlines()
modified+=subprocess.check_output(['git','-C',str(darling),'ls-files','--others','--exclude-standard','--','src/launchd'],text=True).splitlines()
report=dict(installed=False,full_darling_rebuild=False,full_launchd_source_build=True,
    source_commit=expected,complete_source_files=len(sources),
    source_files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
    modified_files={p:hashlib.sha256((darling/p).read_bytes()).hexdigest() for p in modified},
    source_configuration=config,
    binary_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),bootstrap_execution_verified=False,
    variant_root=str(variant.relative_to(root)),
    source_libxpc_sha256=hashlib.sha256((base/'usr/lib/system/libxpc.dylib').read_bytes()).hexdigest())
(root/'artifacts/launchd-source.json').write_text(json.dumps(report,indent=2)+'\n')
print('Built complete launchd source:',output)
