#!/usr/bin/env python3
"""Compile all CoreUtils source files, including real Hash/HMAC/HKDF APIs."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
p=runpy.run_path(str(root/'scripts/pid-generation-source-profile.py'))['profile']()
source=root/'vendor/darling/src/private-frameworks/CoreUtils'
build=root/'runtime/coreutils-crypto-source';build.mkdir(exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
frameworks=build/'include';frameworks.mkdir(exist_ok=True);headers=frameworks/'CoreUtils.framework/Headers';headers.parent.mkdir(exist_ok=True)
if not headers.exists():headers.symlink_to(source/'include/CoreUtils',target_is_directory=True)
cmake=(source/'CMakeLists.txt').read_text();names=re.search(r'\bSOURCES\s+(.*?)\s+DEPENDENCIES',cmake,re.S)[1].split()
assert set(names)=={str(p.relative_to(source)) for p in (source/'src').iterdir() if p.suffix in ['.c','.m']}
objects=build/'objects';objects.mkdir(exist_ok=True)
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
def compile_one(name):
    path=source/name;obj=objects/(path.stem+'.o')
    command=['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-F',str(frameworks),'-fblocks','-fexceptions','-O2','-Wno-deprecated-declarations','-c',str(path),'-o',str(obj)]
    result=subprocess.run(command,capture_output=True,text=True)
    (objects/(path.stem+'.log')).write_text(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError(name+'\n'+result.stderr)
    return dict(source=str(path.relative_to(root)),sha256=digest(str(path.relative_to(root))),object=str(obj.relative_to(root)),object_sha256=digest(str(obj.relative_to(root))),command=command)
with ThreadPoolExecutor(max_workers=8) as pool:manifest=list(pool.map(compile_one,names))
output=build/'frameworks/CoreUtils.framework/Versions/A/CoreUtils';output.parent.mkdir(parents=True,exist_ok=True);pending=output.with_suffix('.pending')
command=['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-L'+str(sdk/'usr/lib/system'),'-install_name','/System/Library/PrivateFrameworks/CoreUtils.framework/Versions/A/CoreUtils','-compatibility_version','1','-current_version','1','-lSystem','-lobjc','-lcommonCrypto','-framework','Foundation',*[str(root/item['object']) for item in manifest],'-o',str(pending)]
subprocess.run(command,check=True)
base=str((root/p['source_runtime']['LINUXCODE_LIBXPC']['path']).parent.relative_to(root))+'/darling-root/System/Library/PrivateFrameworks/CoreUtils.framework/Versions/A/CoreUtils'
def exports(path):return set(re.findall(r'^0x[\da-fA-F]+\s+(\S+)',subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(path)],text=True),re.M))
before=exports(root/base);after=exports(pending);assert before<=after,sorted(before-after)
pending.replace(output)
framework=output.parents[2]
for path,target in [(framework/'Versions/Current','A'),(framework/'CoreUtils','Versions/Current/CoreUtils')]:
    if not path.is_symlink():path.symlink_to(target)
sources=[source/'CMakeLists.txt',*(source/'include').rglob('*.h')]
record=dict(full_CoreUtils_source_build=True,complete_source_files=len(manifest),sources=manifest,source_headers={str(n.relative_to(root)):digest(str(n.relative_to(root))) for n in sources},library=str(output.relative_to(root)),library_sha256=digest(str(output.relative_to(root))),baseline=base,baseline_sha256=digest(base),original_exports_preserved=len(before),added_exports=sorted(after-before),link_command=command,hash_HMAC_HKDF_implemented=True,other_preexisting_CoreUtils_stubs_implemented=False,runtime_execution_verified=False,full_xcode_build_ready=False)
(root/'artifacts/coreutils-crypto-source-build.json').write_text(json.dumps(record,indent=2)+'\n')
print('Built all',len(manifest),'CoreUtils sources; preserved',len(before),'old exports; added',sorted(after-before))
