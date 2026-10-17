#!/usr/bin/env python3
"""Build every Darling CoreCrypto source, preserving the selected old ABI."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import fcntl,hashlib,json,re,subprocess
root=Path(__file__).resolve().parent.parent
repo=root/'vendor/darling/src/external/corecrypto';build=root/'runtime/corecrypto-hkdf-source'
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
names=list(dict.fromkeys(re.search(r'set\(corecrypto_sources(.*?)\n\)',(repo/'CMakeLists.txt').read_text(),re.S)[1].split()))
assert set(names)=={str(p.relative_to(repo)) for p in (repo/'src').glob('*.c')}
build.mkdir(exist_ok=True)
boring=root/'vendor/swift-crypto-3.15.1/Sources/CCryptoBoringSSL'
boring_build=root/'runtime/corecrypto-boringssl'
subprocess.run(['bash',str(root/'scripts/build-corecrypto-boringssl.sh')],check=True)
backend=boring_build/'boring/libCCryptoBoringSSL.a'
backend_record=dict(archive=str(backend.relative_to(root)),archive_sha256=digest(backend),source_revision=subprocess.check_output(['git','-C',str(boring.parents[1]),'rev-parse','HEAD'],text=True).strip(),sources={str(n.relative_to(root)):digest(n) for n in boring.rglob('*') if n.is_file() and (n.suffix in ['.c','.cc','.S','.h','.inc'] or n.name=='CMakeLists.txt')})
def compile_one(name):
    source=repo/name;obj=build/(source.stem+'.o')
    command=['clang-19','-target','x86_64-apple-macos11','-DPLATFORM_MacOSX=1','-DDARLING_CORECRYPTO_BORINGSSL=1','-DDEBUG','-O2','-Wno-return-type','-Wno-deprecated-declarations','-isysroot',str(sdk),'-I',str(repo/'include'),'-I',str(boring/'include'),'-c',str(source),'-o',str(obj)]
    r=subprocess.run(command,capture_output=True,text=True);(build/(source.stem+'.log')).write_text(r.stdout+r.stderr)
    if r.returncode:raise RuntimeError(name+'\n'+r.stderr)
    return dict(source=str(source.relative_to(root)),sha256=digest(source),object=str(obj.relative_to(root)),object_sha256=digest(obj),command=command)
with ThreadPoolExecutor(max_workers=8) as pool:manifest=list(pool.map(compile_one,names))
baselines=['runtime/rootfs/usr/libexec/darling/usr/lib/system/libcorecrypto.dylib','runtime/rootfs/usr/libexec/darling/usr/lib/libCCry.dylib']
def exports(path):return set(re.findall(r'^0x[\da-fA-F]+\s+(\S+)',subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(path)],text=True),re.M))
before=set().union(*(exports(root/n) for n in baselines))
symbols=build/'exports.txt';symbols.write_text((repo/'scripts/exported-symbols.exp').read_text()+'\n_ccdh_ccn_size\n_ccdh_gp_n\n_cczp_n\n')
output=build/'libraries/libcorecrypto.dylib';output.parent.mkdir(exist_ok=True);pending=output.with_suffix('.pending')
command=['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-lSystem','-install_name','/usr/lib/system/libcorecrypto.dylib','-compatibility_version','1','-exported_symbols_list',str(symbols),*[str(root/n['object']) for n in manifest],str(backend),'-o',str(pending)]
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);subprocess.run(command,check=True)
    after=exports(pending);assert before<=after,sorted(before-after)
    pending.replace(output)
record=dict(full_CoreCrypto_source_build=True,complete_source_files=len(manifest),sources=manifest,source_headers={str(n.relative_to(root)):digest(n) for n in [repo/'CMakeLists.txt',repo/'scripts/exported-symbols.exp',*(repo/'include').rglob('*.h')]},baselines={n:digest(n) for n in baselines},library=str(output.relative_to(root)),library_sha256=digest(output),original_exports_preserved=len(before),added_exports=sorted(after-before),export_list=str(symbols.relative_to(root)),export_list_sha256=digest(symbols),link_command=command,BoringSSL=backend_record,HKDF_and_HMAC_runtime_verified=False,other_preexisting_CoreCrypto_stubs_implemented=False)
(root/'artifacts/corecrypto-hkdf-source-build.json').write_text(json.dumps(record,indent=2)+'\n')
print('Built',len(manifest),'sources, preserved',len(before),'exports')
