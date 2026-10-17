#!/usr/bin/env python3
"""Build all Sandbox source files and a coherent private seven-component root."""
from pathlib import Path
import fcntl,hashlib,json,re,runpy,shutil,subprocess
root=Path(__file__).resolve().parent.parent
p=runpy.run_path(str(root/'scripts/typed-new-delete-profile.py'))['profile']()
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
source=root/'vendor/darling/src/sandbox';build=root/'runtime/sandbox-check-source';build.mkdir(exist_ok=True)
sdk=root/'vendor/darling/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';resource=Path(subprocess.check_output(['clang-19','-print-resource-dir'],text=True).strip())
section=re.search(r'set\(sandbox_sources\s+([^)]*)\)',(source/'CMakeLists.txt').read_text())[1];sources=[source/n for n in section.split()];assert len(sources)==3
objects=[]
for path in sources:
    obj=build/(path.stem+'.o');objects.append(str(obj))
    subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-nostdinc','-I',str(source),'-isystem',str(sdk/'usr/include'),'-isystem',str(resource/'include'),'-DDARLING','-DDARWIN','-DPLATFORM_MacOSX','-DTARGET_OS_MAC=1','-D_DARWIN_C_SOURCE','-D__DARWIN_UNIX03','-fPIC','-O2','-Wno-deprecated-declarations','-c',str(path),'-o',str(obj)],check=True)
guest=root/'runtime/rootfs/usr/libexec/darling';output=build/'libsystem_sandbox.dylib';pending=output.with_suffix('.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(guest),'-L',str(guest/'usr/lib/system'),'-install_name','/usr/lib/system/libsystem_sandbox.dylib','-compatibility_version','1.0.0','-ldyld','-lsystem_c','-lsystem_kernel','-lsystem_malloc',*objects,'-o',str(pending)],check=True)
def exports(path):
    text=subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(path)],text=True)
    return set(re.findall(r'^0x[\da-fA-F]+\s+(\S+)',text,re.M))
old=p['source_runtime']['LINUXCODE_SANDBOX'];assert digest(old['path'])==old['sha256']
old_exports=exports(root/old['path']);new_exports=exports(pending);assert old_exports<=new_exports
selected={k:dict(v) for k,v in p['source_runtime'].items()}
base=(root/p['source_runtime']['LINUXCODE_LIBXPC']['path']).parent/'darling-root';variant=build/'darling-root'
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);pending.replace(output)
    staging=build/'darling-root.pending';previous=build/'darling-root.previous'
    for target in [staging,previous]:
        if target.exists():shutil.rmtree(target)
    subprocess.run(['cp','-a','--reflink=auto',str(base),str(staging)],check=True)
    shutil.copy2(output,staging/'usr/lib/system/libsystem_sandbox.dylib')
    for key,item in selected.items():
        if key=='LINUXCODE_SANDBOX':item.update(path=str(output.relative_to(root)),sha256=digest(str(output.relative_to(root))));continue
        assert digest(item['path'])==item['sha256'];target=build/Path(item['path']).name;shutil.copy2(root/item['path'],target);item['path']=str(target.relative_to(root))
    if variant.exists():variant.replace(previous)
    staging.replace(variant)
    if previous.exists():shutil.rmtree(previous)
for key,path in [('LINUXCODE_LAUNCHD','sbin/launchd'),('LINUXCODE_LIBXPC','usr/lib/system/libxpc.dylib'),('LINUXCODE_LIBSYSTEM_KERNEL','usr/lib/system/libsystem_kernel.dylib'),('LINUXCODE_QUARANTINE','usr/lib/system/libquarantine.dylib'),('LINUXCODE_SANDBOX','usr/lib/system/libsystem_sandbox.dylib'),('LINUXCODE_LIBDYLD','usr/lib/system/libdyld.dylib')]:assert digest(str((variant/path).relative_to(root)))==selected[key]['sha256']
files=[*sources,source/'sandbox.h',source/'extension.h',source/'CMakeLists.txt']
report={'library':str(output.relative_to(root)),'library_sha256':digest(str(output.relative_to(root))),'source_files':{str(f.relative_to(root)):digest(str(f.relative_to(root))) for f in files},'full_sandbox_library_source_build':True,'complete_source_files':3,'original_exports_preserved':len(old_exports),'added_exports':sorted(new_exports-old_exports),'previous_source_runtime':p['source_runtime'],'source_runtime':selected,'variant_root':str(variant.relative_to(root)),'previous_variant':str(base.relative_to(root)),'query_MAC_operation':2,'MAC_policy_implemented':False,'approval_grants_implemented':False,'runtime_execution_verified':False,'full_xcode_build_ready':False}
(root/'artifacts/sandbox-check-source-build.json').write_text(json.dumps(report,indent=2)+'\n');print('Built all three source Sandbox files and coherent runtime; no policy grants synthesized')
