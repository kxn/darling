#!/usr/bin/env python3
"""Select the complete source logging implementation in private runtime roots."""
from pathlib import Path
import fcntl,hashlib,json,re,runpy,shutil,subprocess,struct
root=Path(__file__).resolve().parent.parent
parent=runpy.run_path(str(root/'scripts/fsevents-device-runtime-profile.py'))
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
name='artifacts/log-compose-source-build.json';build=json.loads((root/name).read_text());assert build['complete_source_files']==9
folder=root/'runtime/log-compose-runtime';libraries=folder/'libraries';libraries.mkdir(parents=True,exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
base=root/'runtime/rootfs/usr/libexec/darling'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-fPIC','-c',str(root/'scripts/trace-compat.c'),'-o',str(folder/'compat.o')],check=True)
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(base),
    '-install_name','/usr/lib/system/libsystem_trace.dylib','-compatibility_version','1.0.0','-lSystem',
    '-reexport_library',str(root/build['library']),str(folder/'compat.o'),'-o',str(libraries/'libsystem_trace.dylib')],check=True)
# lld can merge this dependency with the umbrella's implicit dependency and
# retain LC_LOAD_DYLIB. Make the intended whole-library reexport explicit.
shim=libraries/'libsystem_trace.dylib';payload=bytearray(shim.read_bytes());at=32;changed=0
for _ in range(struct.unpack_from('<I',payload,16)[0]):
    cmd,size=struct.unpack_from('<II',payload,at)
    if cmd in [0xc,0x8000001f]:
        off=struct.unpack_from('<I',payload,at+8)[0]
        if payload[at+off:at+size].split(b'\0')[0]==b'/usr/lib/libTrace.dylib':
            struct.pack_into('<I',payload,at,0x8000001f);changed+=1
    at+=size
assert changed==1
shim.write_bytes(payload)
exports=lambda path:set(re.findall(r'^(?:0x[\da-fA-F]+|\[re-export\])\s+(\S+)',subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(path)],text=True),re.M))
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    shutil.copy2(root/build['library'],libraries/'libTrace.dylib')
    for diagnostic in [False,True]:
        p=parent['profile'](diagnostic=diagnostic);variant_folder=root/('runtime/log-compose-'+('diagnostic' if diagnostic else 'runtime'));variant_folder.mkdir(exist_ok=True)
        source=root/p['source_fsevents_device']['variant_root'];variant=variant_folder/'darling-root';pending=variant_folder/'darling-root.pending'
        assert exports(source/'usr/lib/system/libsystem_trace.dylib')<=exports(libraries/'libsystem_trace.dylib')|exports(libraries/'libTrace.dylib')
        assert '__os_log_send_and_compose_impl' in exports(libraries/'libTrace.dylib')
        if pending.exists():shutil.rmtree(pending)
        subprocess.run(['cp','-a','--reflink=auto',str(source),str(pending)],check=True)
        shutil.copy2(libraries/'libsystem_trace.dylib',pending/'usr/lib/system/libsystem_trace.dylib')
        shutil.copy2(libraries/'libTrace.dylib',pending/'usr/lib/libTrace.dylib')
        selected={k:dict(item) for k,item in p['source_runtime'].items()}
        for item in selected.values():
            target=variant_folder/Path(item['path']).name;shutil.copy2(root/item['path'],target)
            item.update(path=str(target.relative_to(root)),sha256=digest(target))
        if variant.exists():shutil.rmtree(variant)
        pending.replace(variant)
        report=dict(previous_source_runtime=p['source_runtime'],source_runtime=selected,variant_root=str(variant.relative_to(root)),
                    source_build=name,source_build_sha256=digest(name),source_libtrace=build,
                    compatibility_source='scripts/trace-compat.c',compatibility_source_sha256=digest('scripts/trace-compat.c'),
                    compatibility_library=str((libraries/'libsystem_trace.dylib').relative_to(root)),compatibility_library_sha256=digest(libraries/'libsystem_trace.dylib'),
                    library_directory=str(libraries.relative_to(root)),diagnostic_policy=p['coreservices_diagnostic_policy'],
                    original_policy_override=diagnostic,old_exports_available_through_existing_LC_REEXPORT_DYLIB=True,default_entry_promoted=False,runtime_execution_verified=False,full_xcode_build_ready=False)
        (root/('artifacts/log-compose-'+('diagnostic' if diagnostic else 'runtime')+'-stage.json')).write_text(json.dumps(report,indent=2)+'\n')
print('Staged source log composition; original default runtime and strict-policy resources preserved')
