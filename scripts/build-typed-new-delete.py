#!/usr/bin/env python3
"""Build source typed C++ operator fallbacks, preserving the old libc++ image."""
from pathlib import Path
import fcntl,hashlib,json,re,runpy,struct,subprocess
root=Path(__file__).resolve().parent.parent
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
source='vendor/darling/src/external/libcxx/src/typed_new_delete.cpp'
cmake='vendor/darling/src/external/libcxx/src/CMakeLists.txt'
base='runtime/native-library-stage/libc++.1.dylib'
build=root/'runtime/typed-new-delete-source';libraries=build/'libraries';libraries.mkdir(parents=True,exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
obj=build/'typed_new_delete.o'
subprocess.run(['clang++-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-nostdinc++','-isystem',str(sdk/'usr/include/c++/v1'),'-std=c++17','-O2','-fPIC','-c',str(root/source),'-o',str(obj)],check=True)
names=['__ZnwmSt19__type_descriptor_t','__ZnamSt19__type_descriptor_t','__ZdlPvSt19__type_descriptor_t','__ZdaPvSt19__type_descriptor_t']
config=json.loads((root/'config/libcxx-to-chars.json').read_text())
previous=json.loads((root/'artifacts/libcxx-to-chars.json').read_text())
assert digest(base)==previous['library_sha256']
for name,sha in config['existing_objects'].items():assert digest(name)==sha
guest=root/'runtime/rootfs/usr/libexec/darling'
backend=guest/'usr/lib/libc++0.dylib';assert digest(str(backend.relative_to(root)))==config['existing_backend_sha256']
inputs=[root/n for n in config['existing_objects']]+[root/'runtime/libcxx-to-chars'/n for n in ['to-chars.o','d2s.o','d2fixed.o','f2s.o']]
link=['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-install_name','/usr/lib/libc++.1.dylib','-compatibility_version','1.0.0','-current_version','1.0.0','-syslibroot',str(guest),'-L',str(guest/'usr/lib'),'-lSystem','-reexport_library',str(backend),*[str(n) for n in inputs]]
# The existing image has only 32 bytes of header padding. Reproduce its complete payload
# (only the output-dependent UUID may differ) before relinking the same verified objects with the new source component.
control=build/'baseline-relink.dylib';subprocess.run([*link,'-o',str(control)],check=True)
original=(root/base).read_bytes();relinked=control.read_bytes();assert len(original)==len(relinked)
at=32;uuid_range=None
for _ in range(struct.unpack_from('<I',original,16)[0]):
    command,size=struct.unpack_from('<II',original,at)
    if command==0x1b:uuid_range=(at+8,at+24)
    at+=size
assert uuid_range is not None
assert all(a==b or uuid_range[0]<=i<uuid_range[1] for i,(a,b) in enumerate(zip(original,relinked))),'Baseline relink differs beyond the linker UUID'

target=libraries/'libc++.1.dylib'
temporary=target.with_suffix('.pending');subprocess.run([*link,str(obj),'-o',str(temporary)],check=True)
def exports(path):
    text=subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(path)],text=True)
    return set(re.findall(r'^0x[0-9A-Fa-f]+\s+(\S+)',text,re.M))
old=exports(root/base);new=exports(temporary);assert new-old==set(names) and old<=new
control_folder=build/'unsorted-control';control_folder.mkdir(exist_ok=True)
unsorted=control_folder/'libc++.1.dylib';unsorted.write_bytes(temporary.read_bytes())
payload,weak_order=runpy.run_path(str(root/'scripts/normalize-macho-weak-bind.py'))['normalize'](temporary.read_bytes());temporary.write_bytes(payload)
assert exports(temporary)==new
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);temporary.replace(target)
record={'source':source,'source_sha256':digest(source),'cmake':cmake,'cmake_sha256':digest(cmake),'base':base,'base_sha256':digest(base),'library':str(target.relative_to(root)),'library_sha256':digest(str(target.relative_to(root))),'baseline_relink':str(control.relative_to(root)),'baseline_relink_sha256':digest(str(control.relative_to(root))),'baseline_relink_byte_identical':original==relinked,'baseline_relink_only_UUID_differs':True,'baseline_UUID_range':uuid_range,'old_object_inputs':{str(n.relative_to(root)):digest(str(n.relative_to(root))) for n in inputs},'backend':str(backend.relative_to(root)),'backend_sha256':digest(str(backend.relative_to(root))),'original_direct_exports_preserved':len(old),'exports':names,'weak_bind_normalization':weak_order,'unsorted_control':str(unsorted.relative_to(root)),'unsorted_control_sha256':digest(str(unsorted.relative_to(root))),'type_partition_isolation_implemented':False,'full_libcxx_build':False,'runtime_execution_verified':False,'full_xcode_build_ready':False}
(root/'artifacts/typed-new-delete-source-build.json').write_text(json.dumps(record,indent=2)+'\n')
print('Built four real typed C++ allocation fallbacks; type partitions unsupported')
