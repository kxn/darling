#!/usr/bin/env python3
"""Select complete source CoreUtils and actual native Quarantine proc APIs."""
from pathlib import Path
import fcntl,hashlib,json,re,runpy,shutil,subprocess
root=Path(__file__).resolve().parent.parent
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
p=runpy.run_path(str(root/'scripts/mobile-device-native-profile.py'))['profile']()
crypto=json.loads((root/'artifacts/coreutils-crypto-source-build.json').read_text());assert crypto['full_CoreUtils_source_build'] and crypto['complete_source_files']==132
assert digest(crypto['library'])==crypto['library_sha256']
native='runtime/rebuilt-quarantine-proc-native/libquarantine.dylib';report='runtime/rebuilt-quarantine-proc-native/reconstruction.json';reconstruction=json.loads((root/report).read_text())
assert digest(native)==reconstruction['staged_image_sha256'];assert not reconstruction['backend_call_overrides']
assert set(reconstruction['redirected_imports'])=={'_malloc_type_malloc','_malloc_type_calloc'}
assert not reconstruction['modern_adapter']
typed=json.loads((root/'artifacts/typed-malloc-source-stage.json').read_text());assert typed['upstream_source_bytes_unchanged']
assert digest(typed['helper'])==typed['helper_sha256']
exports=subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(root/native)],text=True)
names=[n for n in re.findall(r'^0x[\da-fA-F]+\s+(\S+)',exports,re.M) if n.startswith('__qtn_proc_') or n=='_qtn_proc_init_with_pid']
assert len(names)==22
build=root/'runtime/crypto-quarantine-runtime';build.mkdir(exist_ok=True)
old=p['source_runtime']['LINUXCODE_QUARANTINE'];provider=build/'libraries/libDarlingNativeQuarantine.dylib';provider.parent.mkdir(exist_ok=True)
source=root/'vendor/darling/src/quarantine';sdk=root/'vendor/darling/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
source_names=re.search(r'set\(quarantine_sources\s+([^)]*)\)',(source/'CMakeLists.txt').read_text())[1].split();assert len(source_names)==2
objects=[];quarantine_sources={}
for name in source_names:
    path=source/name;obj=build/(path.stem+'.o');objects.append(str(obj));quarantine_sources[str(path.relative_to(root))]=digest(str(path.relative_to(root)))
    subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-I'+str(source/'include'),'-DDARLING','-DDARWIN','-DPLATFORM_MacOSX','-DTARGET_OS_MAC=1','-D_DARWIN_C_SOURCE','-D__DARWIN_UNIX03','-fPIC','-O2','-c',str(path),'-o',str(obj)],check=True)
guest=root/'runtime/rootfs/usr/libexec/darling';relinked=build/'source-libquarantine.dylib'
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-headerpad','400','-syslibroot',str(guest),'-L'+str(guest/'usr/lib/system'),'-install_name','/usr/lib/system/libquarantine.dylib','-compatibility_version','1.0.0','-lsystem_c','-ldyld','-lsystem_malloc','-lsystem_kernel','-lsystem_pthread',*objects,'-o',str(relinked)],check=True)
payload,changes=runpy.run_path(str(root/'scripts/macho-named-reexport.py'))['add'](relinked.read_bytes(),'/usr/lib/libDarlingNativeQuarantine.dylib',names)
for path in [source/'CMakeLists.txt',*(source/'include').rglob('*.h')]:quarantine_sources[str(path.relative_to(root))]=digest(str(path.relative_to(root)))
listing=lambda path:subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(path)],text=True)
read_exports=lambda text:set(re.findall(r'^(?:0x[\da-fA-F]+|\[re-export\])\s+(\S+)',text,re.M))
before=read_exports(listing(root/old['path']));after=read_exports(listing(relinked))|set(names)
assert before<=after and after-before==set(names)
selected={k:dict(v) for k,v in p['source_runtime'].items()}
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    temporary=build/'darling-root.pending';variant=build/'darling-root';previous=build/'darling-root.previous'
    for path in [temporary,previous]:
        if path.exists():shutil.rmtree(path)
    base=(root/p['source_runtime']['LINUXCODE_LIBXPC']['path']).parent/'darling-root'
    subprocess.run(['cp','-a','--reflink=auto',str(base),str(temporary)],check=True)
    library=build/'libquarantine.dylib';library.write_bytes(payload);shutil.copy2(library,temporary/'usr/lib/system/libquarantine.dylib');shutil.copy2(root/native,provider)
    # libSystem may load this dependency before /usr/bin/env sets DYLD paths.
    shutil.copy2(provider,temporary/'usr/lib/libDarlingNativeQuarantine.dylib')
    shutil.copy2(root/typed['helper'],temporary/'usr/lib/libDarlingTypedMalloc.dylib')
    for key,item in selected.items():
        if key=='LINUXCODE_QUARANTINE':item.update(path=str(library.relative_to(root)),sha256=digest(str(library.relative_to(root))));continue
        target=build/Path(item['path']).name;shutil.copy2(root/item['path'],target);item['path']=str(target.relative_to(root))
    if variant.exists():variant.replace(previous)
    temporary.replace(variant)
    if previous.exists():shutil.rmtree(previous)
for key,path in [('LINUXCODE_LAUNCHD','sbin/launchd'),('LINUXCODE_LIBXPC','usr/lib/system/libxpc.dylib'),('LINUXCODE_LIBSYSTEM_KERNEL','usr/lib/system/libsystem_kernel.dylib'),('LINUXCODE_QUARANTINE','usr/lib/system/libquarantine.dylib'),('LINUXCODE_SANDBOX','usr/lib/system/libsystem_sandbox.dylib'),('LINUXCODE_LIBDYLD','usr/lib/system/libdyld.dylib')]:assert digest(str((variant/path).relative_to(root)))==selected[key]['sha256']
record=dict(source_runtime=selected,previous_source_runtime=p['source_runtime'],coreutils_build='artifacts/coreutils-crypto-source-build.json',coreutils_build_sha256=digest('artifacts/coreutils-crypto-source-build.json'),native=native,native_sha256=digest(native),native_provider=str(provider.relative_to(root)),native_provider_sha256=digest(str(provider.relative_to(root))),native_reconstruction=report,native_reconstruction_sha256=digest(report),original_quarantine=old,quarantine_source_files=quarantine_sources,full_quarantine_source_files=len(source_names),relinked_quarantine=str(relinked.relative_to(root)),relinked_quarantine_sha256=digest(str(relinked.relative_to(root))),proc_exports=names,export_changes=changes,policy_calls_implemented=False,full_xcode_build_ready=False)
record['bootstrap_helpers']={str((variant/'usr/lib'/name).relative_to(root)):digest(str((variant/'usr/lib'/name).relative_to(root))) for name in ['libDarlingNativeQuarantine.dylib','libDarlingTypedMalloc.dylib']}
record['original_quarantine_exports_preserved']=len(before)
(root/'artifacts/crypto-quarantine-runtime-stage.json').write_text(json.dumps(record,indent=2)+'\n');print('Selected source CoreUtils and',len(names),'actual native process Quarantine APIs; unsupported backend errors retained')
