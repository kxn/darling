#!/usr/bin/env python3
"""Add the real expected exception runtime to the verified libc++ wrapper."""
from pathlib import Path
import fcntl,hashlib,json,re,runpy,struct,subprocess
root=Path(__file__).resolve().parent.parent
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
repo=root/'vendor/llvm-charconv';commit='2078da43e25a4623cab2d0d60decddf709aaea28'
assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==commit
source='vendor/darling/src/external/libcxx/src/expected_exception.cpp'
header='vendor/darling/src/external/libcxx/src/include/expected_exception.h'
upstream=repo/'libcxx/src/expected.cpp';upstream_header=repo/'libcxx/include/__expected/bad_expected_access.h'
method='const char* bad_expected_access<void>::what() const noexcept { return "bad access to std::expected"; }'
assert method in upstream.read_text() and method in (root/source).read_text()
original=upstream_header.read_text()
for line in (root/header).read_text().splitlines():
    if ' = default;' in line:assert line in original
base='runtime/typed-new-delete-source/libraries/libc++.1.dylib'
old=json.loads((root/'artifacts/typed-new-delete-source-build.json').read_text());assert digest(base)==old['library_sha256']
for name,sha in old['old_object_inputs'].items():assert digest(name)==sha
build=root/'runtime/expected-access-source';libraries=build/'libraries';libraries.mkdir(parents=True,exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
obj=build/'expected_exception.o'
subprocess.run(['clang++-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-nostdinc++','-isystem',str(sdk/'usr/include/c++/v1'),'-std=c++17','-O2','-fPIC','-c',str(root/source),'-o',str(obj)],check=True)
inputs=[root/n for n in old['old_object_inputs']]+[root/'runtime/typed-new-delete-source/typed_new_delete.o']
guest=root/'runtime/rootfs/usr/libexec/darling'
link=['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-install_name','/usr/lib/libc++.1.dylib','-compatibility_version','1.0.0','-current_version','1.0.0','-syslibroot',str(guest),'-L',str(guest/'usr/lib'),'-lSystem','-reexport_library',str(root/old['backend']),*[str(n) for n in inputs]]
normalizer=runpy.run_path(str(root/'scripts/normalize-macho-weak-bind.py'))['normalize']
control=build/'baseline-relink.dylib';subprocess.run([*link,'-o',str(control)],check=True);payload,_=normalizer(control.read_bytes());control.write_bytes(payload)
previous=(root/base).read_bytes();baseline=control.read_bytes();assert len(previous)==len(baseline);at=32;uuid=None
for _ in range(struct.unpack_from('<I',previous,16)[0]):
    command,size=struct.unpack_from('<II',previous,at)
    if command==0x1b:uuid=[at+8,at+24]
    at+=size
assert uuid is not None and all(a==b or uuid[0]<=i<uuid[1] for i,(a,b) in enumerate(zip(previous,baseline)))
target=libraries/'libc++.1.dylib';pending=target.with_suffix('.pending');subprocess.run([*link,str(obj),'-o',str(pending)],check=True)
raw=build/'unprocessed-libc++.1.dylib';raw.write_bytes(pending.read_bytes());payload,normalization=normalizer(raw.read_bytes());pending.write_bytes(payload)
def exports(path):
    listing=subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(path)],text=True)
    return set(re.findall(r'^0x[0-9A-Fa-f]+\s+(\S+)',listing,re.M))
before=exports(root/base);after=exports(pending);required={'__ZNKSt3__119bad_expected_accessIvE4whatEv','__ZTINSt3__119bad_expected_accessIvEE','__ZTSNSt3__119bad_expected_accessIvEE','__ZTVNSt3__119bad_expected_accessIvEE'}
assert before<=after and after-before==required,(after-before)
with (root/'runtime/session.lock').open('a') as lock:fcntl.flock(lock,fcntl.LOCK_EX);pending.replace(target)
paths=[source,header,'vendor/darling/src/external/libcxx/src/CMakeLists.txt']
record={'library':str(target.relative_to(root)),'library_sha256':digest(str(target.relative_to(root))),'base':base,'base_sha256':digest(base),'source_files':{n:digest(n) for n in paths},'official_commit':commit,'official_source_sha256':digest(str(upstream.relative_to(root))),'official_header_sha256':digest(str(upstream_header.relative_to(root))),'what_body_unchanged':True,'class_header_adaptations':['Use existing <exception> build headers instead of modern internal includes','Provide the older visibility macro alias','Always build the out-of-line key function; no inline availability fallback'],'existing_object_inputs':{str(n.relative_to(root)):digest(str(n.relative_to(root))) for n in inputs},'baseline':str(control.relative_to(root)),'baseline_sha256':digest(str(control.relative_to(root))),'baseline_only_UUID_differs':True,'baseline_UUID_range':uuid,'original_direct_exports_preserved':len(before),'added_exports':sorted(required),'unprocessed':str(raw.relative_to(root)),'unprocessed_sha256':digest(str(raw.relative_to(root))),'weak_bind_normalization':normalization,'full_libcxx_build':False,'runtime_execution_verified':False,'full_xcode_build_ready':False}
(root/'artifacts/expected-access-source-build.json').write_text(json.dumps(record,indent=2)+'\n');print('Built official expected exception key function and compiler-generated typeinfo/vtable; existing',len(before),'exports retained')
