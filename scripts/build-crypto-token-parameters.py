#!/usr/bin/env python3
"""Build the actual native-valued token parameter over the existing framework."""
from pathlib import Path
import fcntl,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent;digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
reference='artifacts/crypto-token-parameters-native-reference.json';r=json.loads((root/reference).read_text());assert digest(r['provider'])==r['provider_sha256']
source='vendor/darling/src/frameworks/CryptoTokenKit/src/TKClientTokenParameters.m';assert '@"'+r['value']+'"' in (root/source).read_text()
build=root/'runtime/crypto-token-parameters-source';build.mkdir(exist_ok=True);sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';obj=build/'constant.o'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-I',str(root/'vendor/darling/src/frameworks/CryptoTokenKit/include'),'-c',str(root/source),'-o',str(obj)],check=True)
library=build/'libraries/libDarlingCryptoTokenParameters.dylib';library.parent.mkdir(exist_ok=True)
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-framework','Foundation','-lobjc','-lSystem','-install_name','/usr/lib/'+library.name,str(obj),'-o',str(library)],check=True)
base='runtime/crypto-token-error-source/frameworks/CryptoTokenKit.framework/Versions/A/CryptoTokenKit'
payload,changes=runpy.run_path(str(root/'scripts/macho-named-reexport.py'))['add']((root/base).read_bytes(),'/usr/lib/'+library.name,[r['symbol']])
framework=build/'frameworks/CryptoTokenKit.framework';output=framework/'Versions/A/CryptoTokenKit';output.parent.mkdir(parents=True,exist_ok=True)
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);output.write_bytes(payload)
    for path,destination in [(framework/'Versions/Current','A'),(framework/'CryptoTokenKit','Versions/Current/CryptoTokenKit')]:
        if not path.is_symlink():path.symlink_to(destination)
record=dict(source=source,source_sha256=digest(source),source_list='vendor/darling/src/frameworks/CryptoTokenKit/CMakeLists.txt',source_list_sha256=digest('vendor/darling/src/frameworks/CryptoTokenKit/CMakeLists.txt'),library=str(library.relative_to(root)),library_sha256=digest(library),framework=str(output.relative_to(root)),framework_sha256=digest(output),base=base,base_sha256=digest(base),reference=reference,reference_sha256=digest(reference),native_value=r['value'],export_changes=changes,hardware_token_service_implemented=False,runtime_execution_verified=False)
(root/'artifacts/crypto-token-parameters-source-build.json').write_text(json.dumps(record,indent=2)+'\n');print('Built real token parameter',r['value'])
