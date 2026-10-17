#!/usr/bin/env python3
"""Build all configured DiskManagement sources with the native-valued nil entry."""
from pathlib import Path
import fcntl,hashlib,json,re,struct,subprocess
root=Path(__file__).resolve().parent.parent
repo=root/'vendor/darling/src/private-frameworks/DiskManagement';build=root/'runtime/diskmanagement-nserror-source';build.mkdir(exist_ok=True)
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
reference=json.loads((root/'artifacts/diskmanagement-nserror-native-reference.json').read_text())
assert digest(root/reference['provider'])==reference['provider_sha256']
assert reference['machine_code']=='554889e531c05dc3' and reference['independently_read_from_actual_dyld_cache']
cmake=(repo/'CMakeLists.txt').read_text();assert 'file(GLOB DM_C src/*.c)' in cmake and 'file(GLOB DM_OBJC src/*.m)' in cmake
sources=sorted((repo/'src').glob('*.c'))+sorted((repo/'src').glob('*.m'));assert len(sources)==23
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
guest=root/'runtime/rootfs/usr/libexec/darling';objects=[]
for source in sources:
    obj=build/(source.stem+'.o');objects.append(obj)
    subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-I',str(repo/'include'),'-fblocks','-O2','-w','-c',str(source),'-o',str(obj)],check=True)
framework=build/'frameworks/DiskManagement.framework';output=framework/'Versions/A/DiskManagement';output.parent.mkdir(parents=True,exist_ok=True);pending=output.with_name('DiskManagement.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-install_name','/System/Library/PrivateFrameworks/DiskManagement.framework/Versions/A/DiskManagement','-compatibility_version','1.0.0','-current_version','1.0.0','-syslibroot',str(guest),'-F',str(guest/'System/Library/Frameworks'),'-lSystem','-lobjc','-framework','Foundation',*[str(p) for p in objects],'-o',str(pending)],check=True)
baseline=guest/'System/Library/PrivateFrameworks/DiskManagement.framework/Versions/A/DiskManagement'
exports=lambda p:set(re.findall(r'^0x[\da-fA-F]+\s+(\S+)',subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(p)],text=True),re.M))
old,new=exports(baseline),exports(pending);assert old<=new and new-old=={'_DMNSError'}
symbols={p[2]:int(p[0],16) for row in subprocess.check_output(['llvm-nm-19','--defined-only',str(pending)],text=True).splitlines() if len(p:=row.split())==3}
data=pending.read_bytes();at=32;segments=[]
for _ in range(struct.unpack_from('<I',data,16)[0]):
    cmd,size=struct.unpack_from('<II',data,at)
    if cmd==0x19:segments.append(struct.unpack_from('<QQQQ',data,at+24))
    at+=size
address=symbols['_DMNSError'];segment=next(s for s in segments if s[0]<=address<s[0]+s[3]);offset=segment[2]+address-segment[0]
assert data[offset:offset+8]==bytes.fromhex(reference['machine_code']),'Source entry must compile to the same complete eight-byte native function'
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);pending.replace(output)
    for p,target in [(framework/'Versions/Current','A'),(framework/'DiskManagement','Versions/Current/DiskManagement')]:
        if not p.is_symlink():p.symlink_to(target)
report=dict(full_framework_source_build=True,complete_source_files=len(sources),source_files={str(p.relative_to(root)):digest(p) for p in [*sources,repo/'CMakeLists.txt',*sorted((repo/'include/DiskManagement').glob('*.h'))]},framework=str(output.relative_to(root)),framework_sha256=digest(output),baseline=str(baseline.relative_to(root)),baseline_sha256=digest(baseline),reference='artifacts/diskmanagement-nserror-native-reference.json',reference_sha256=digest(root/'artifacts/diskmanagement-nserror-native-reference.json'),original_exports_preserved=len(old),source_exports=len(new),complete_DMNSError_instructions_identical_to_native=True,generic_disk_manager_stubs_implemented=False,disk_operations_implemented=False,runtime_execution_verified=False,full_xcode_build_ready=False)
(root/'artifacts/diskmanagement-nserror-source-build.json').write_text(json.dumps(report,indent=2)+'\n');print('Compiled all 23 source files; native eight-byte entry identical; original disk-manager stubs remain')
