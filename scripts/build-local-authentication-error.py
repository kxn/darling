#!/usr/bin/env python3
"""Rebuild the complete existing LA framework plus its native error domain."""
from pathlib import Path
import fcntl,hashlib,json,re,subprocess
root=Path(__file__).resolve().parent.parent;digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
repo=root/'vendor/darling/src/frameworks/LocalAuthentication';build=root/'runtime/local-authentication-error-source';build.mkdir(exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
names=re.search(r'\bSOURCES\s+(.*?)\s+DEPENDENCIES',(repo/'CMakeLists.txt').read_text(),re.S)[1].split();assert set(names)=={str(n.relative_to(repo)) for n in (repo/'src').iterdir() if n.suffix in ['.c','.m']};manifest=[]
for name in names:
    source=repo/name;obj=build/(source.stem+'.o');command=['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-I',str(repo/'include'),'-O2','-Wno-deprecated-declarations','-c',str(source),'-o',str(obj)];subprocess.run(command,check=True);manifest.append(dict(source=str(source.relative_to(root)),sha256=digest(source),object=str(obj.relative_to(root)),object_sha256=digest(obj),command=command))
framework=build/'frameworks/LocalAuthentication.framework';output=framework/'Versions/A/LocalAuthentication';output.parent.mkdir(parents=True,exist_ok=True)
link=['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-lSystem','-lobjc','-framework','Foundation','-install_name','/System/Library/Frameworks/LocalAuthentication.framework/Versions/A/LocalAuthentication','-compatibility_version','1','-current_version','240.50.25',*[str(root/item['object']) for item in manifest],'-o',str(output.with_suffix('.pending'))]
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);subprocess.run(link,check=True);output.with_suffix('.pending').replace(output)
    for path,destination in [(framework/'Versions/Current','A'),(framework/'LocalAuthentication','Versions/Current/LocalAuthentication')]:
        if not path.is_symlink():path.symlink_to(destination)
record=dict(full_framework_source_build=True,sources=manifest,source_headers={str(n.relative_to(root)):digest(n) for n in [repo/'CMakeLists.txt',*(repo/'include').rglob('*.h')]},complete_source_files=len(manifest),framework=str(output.relative_to(root)),framework_sha256=digest(output),link_command=link,authentication_implemented=False,existing_LAContext_forwarding_implemented=False,runtime_execution_verified=False)
(root/'artifacts/local-authentication-error-source-build.json').write_text(json.dumps(record,indent=2)+'\n');print('Built all',len(names),'LA sources; authentication remains unimplemented')
