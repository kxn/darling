#!/usr/bin/env python3
"""Build all three Darling coreservices sources in a private coherent root."""
from pathlib import Path
import argparse,fcntl,hashlib,json,re,runpy,shutil,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('--baseline',action='store_true');args=parser.parse_args()
parent=runpy.run_path(str(root/'scripts/commoncrypto-original-profile.py'))['profile']()
repo=root/'vendor/darling/src/libsystem_coreservices';build=root/('runtime/coreservices-directories-'+('baseline' if args.baseline else 'source-v2'));build.mkdir(exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
base=(root/parent['source_runtime']['LINUXCODE_LIBDYLD']['path']).parent/'darling-root'
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
names=re.search(r'add_darling_library\(system_coreservices SHARED (.*?)\)',(repo/'CMakeLists.txt').read_text())[1].split();assert set(names)=={p.name for p in repo.glob('*.c')}
manifest=[]
for name in names:
    source=repo/name
    if args.baseline and name=='dirhelper.c':source=root/next(iter(json.loads((root/'artifacts/dirhelper-source-history/manifest.json').read_text()).values()))['archived']
    obj=build/(Path(name).stem+'.o')
    command=['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-I',str(repo),'-O2','-fPIC','-D__DARWIN_UNIX03','-Wno-deprecated-declarations','-x','c','-c',str(source),'-o',str(obj)]
    subprocess.run(command,check=True);manifest.append(dict(source=str(source.relative_to(root)),sha256=digest(source),object=str(obj.relative_to(root)),object_sha256=digest(obj),command=command))
library=build/'libsystem_coreservices.dylib';pending=library.with_suffix('.pending')
link=['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(base),'-L'+str(base/'usr/lib/system'),'-lsystem_c',*(['-lsystem_malloc'] if not args.baseline else []),'-ldyld','-lsystem_platform','-lsystem_pthread','-lsystem_kernel','-install_name','/usr/lib/system/libsystem_coreservices.dylib','-compatibility_version','1',*[str(root/i['object']) for i in manifest],'-o',str(pending)]
subprocess.run(link,check=True)
exports=lambda p:set(re.findall(r'^0x[\da-fA-F]+\s+(\S+)',subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(p)],text=True),re.M))
baseline=base/'usr/lib/system/libsystem_coreservices.dylib';old,new=exports(baseline),exports(pending);assert old<=new,old-new
variant=build/'darling-root'
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    if variant.exists():
        assert digest(pending)==digest(library)==digest(variant/'usr/lib/system/libsystem_coreservices.dylib'),'Use a fresh output variant for changed code'
        pending.unlink()
    else:
        pending.replace(library);subprocess.run(['cp','-a','--reflink=auto',str(base),str(variant)],check=True);shutil.copy2(library,variant/'usr/lib/system/libsystem_coreservices.dylib')
    selected={}
    for key,item in parent['source_runtime'].items():
        dest=build/Path(item['path']).name;shutil.copy2(root/item['path'],dest);assert digest(dest)==item['sha256'];selected[key]=dict(path=str(dest.relative_to(root)),sha256=digest(dest))
headers={str(n.relative_to(root)):digest(n) for n in [repo/'CMakeLists.txt',repo/'dirhelper_priv.h']}
if args.baseline:
    original_headers=json.loads((root/'artifacts/dirhelper-source-history/manifest.json').read_text());headers['vendor/darling/src/libsystem_coreservices/CMakeLists.txt']=original_headers['vendor/darling/src/libsystem_coreservices/CMakeLists.txt']['sha256']
record=dict(full_component_source_build=True,complete_source_files=len(manifest),sources=manifest,source_headers=headers,previous_source_runtime=parent['source_runtime'],source_runtime=selected,library=str(library.relative_to(root)),library_sha256=digest(library),baseline=str(baseline.relative_to(root)),baseline_sha256=digest(baseline),exports_preserved=len(old),exports=len(new),link_command=link,variant_root=str(variant.relative_to(root)),pre_fix_control=args.baseline,full_xcode_build_ready=False)
name='artifacts/coreservices-directories-'+('baseline' if args.baseline else 'source-v2')+'-build.json';(root/name).write_text(json.dumps(record,indent=2)+'\n');print('Built',len(names),'sources;',len(old),'exports preserved')
