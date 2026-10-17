#!/usr/bin/env python3
"""Build the real error-domain constant while preserving the existing framework."""
from pathlib import Path
import fcntl,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent;digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
reference_name='artifacts/crypto-token-error-native-reference.json';reference=json.loads((root/reference_name).read_text());assert digest(reference['provider'])==reference['provider_sha256']
source='vendor/darling/src/frameworks/CryptoTokenKit/src/TKError.m';assert '@"'+reference['value']+'"' in (root/source).read_text()
build=root/'runtime/crypto-token-error-source';build.mkdir(exist_ok=True);sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';obj=build/'constant.o'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-c',str(root/source),'-o',str(obj)],check=True)
library=build/'libraries/libDarlingCryptoTokenError.dylib';library.parent.mkdir(exist_ok=True)
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-framework','Foundation','-framework','CoreFoundation','-lobjc','-lSystem','-install_name','/usr/lib/'+library.name,str(obj),'-o',str(library)],check=True)
base='runtime/rootfs/usr/libexec/darling/System/Library/Frameworks/CryptoTokenKit.framework/Versions/A/CryptoTokenKit'
thin=build/'CryptoTokenKit.x86_64';subprocess.run(['llvm-lipo-19',str(root/base),'-thin','x86_64','-output',str(thin)],check=True)
payload,changes=runpy.run_path(str(root/'scripts/macho-named-reexport.py'))['add'](thin.read_bytes(),'/usr/lib/'+library.name,[reference['symbol']])
framework=build/'frameworks/CryptoTokenKit.framework';output=framework/'Versions/A/CryptoTokenKit';output.parent.mkdir(parents=True,exist_ok=True)
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);output.write_bytes(payload)
 for path,destination in [(framework/'Versions/Current','A'),(framework/'CryptoTokenKit','Versions/Current/CryptoTokenKit')]:
  if not path.is_symlink():path.symlink_to(destination)
record=dict(source=source,source_sha256=digest(source),source_list='vendor/darling/src/frameworks/CryptoTokenKit/CMakeLists.txt',source_list_sha256=digest('vendor/darling/src/frameworks/CryptoTokenKit/CMakeLists.txt'),library=str(library.relative_to(root)),library_sha256=digest(str(library.relative_to(root))),framework=str(output.relative_to(root)),framework_sha256=digest(str(output.relative_to(root))),base=base,base_sha256=digest(base),thin_base=str(thin.relative_to(root)),thin_base_sha256=digest(str(thin.relative_to(root))),reference=reference_name,reference_sha256=digest(reference_name),value=reference['value'],export_changes=changes,full_CryptoTokenKit_source_build=False,existing_token_service_stubs_implemented=False,runtime_execution_verified=False)
(root/'artifacts/crypto-token-error-source-build.json').write_text(json.dumps(record,indent=2)+'\n');print('Compiled source TKErrorDomain with native value',reference['value'],'; existing token-service stubs remain unsupported')
