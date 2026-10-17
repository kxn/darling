#!/usr/bin/env python3
"""Add verified native algorithm identifiers; no hardware or crypto success stubs."""
from pathlib import Path
import fcntl,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent;digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
reference='artifacts/security-cryptokit-constants-native-reference.json';r=json.loads((root/reference).read_text());assert digest(r['provider'])==r['provider_sha256']
source='vendor/darling/src/external/security/OSX/sec/Security/SecCryptoKitConstants.c';text=(root/source).read_text()
for name,value in r['values'].items():assert 'const CFStringRef '+name[1:]+' = CFSTR('+json.dumps(value)+');' in text
build=root/'runtime/security-cryptokit-constants';build.mkdir(exist_ok=True);sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';obj=build/'constant.o'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-c',str(root/source),'-o',str(obj)],check=True)
library=build/'libraries/libDarlingSecurityCryptoKitConstants.dylib';library.parent.mkdir(exist_ok=True)
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-framework','CoreFoundation','-lSystem','-install_name','/usr/lib/'+library.name,str(obj),'-o',str(library)],check=True)
base='runtime/security-device-constants/frameworks/Security.framework/Versions/A/Security'
payload,changes=runpy.run_path(str(root/'scripts/macho-named-reexport.py'))['add']((root/base).read_bytes(),'/usr/lib/'+library.name,list(r['values']))
framework=build/'frameworks/Security.framework';output=framework/'Versions/A/Security';output.parent.mkdir(parents=True,exist_ok=True)
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);output.write_bytes(payload)
    for path,destination in [(framework/'Versions/Current','A'),(framework/'Security','Versions/Current/Security')]:
        if not path.is_symlink():path.symlink_to(destination)
record=dict(source=source,source_sha256=digest(source),source_list='vendor/darling/src/external/security/OSX/sec/Security/CMakeLists.txt',source_list_sha256=digest('vendor/darling/src/external/security/OSX/sec/Security/CMakeLists.txt'),library=str(library.relative_to(root)),library_sha256=digest(library),framework=str(output.relative_to(root)),framework_sha256=digest(output),base=base,base_sha256=digest(base),reference=reference,reference_sha256=digest(reference),native_values=r['values'],export_changes=changes,hardware_services_implemented=False,runtime_execution_verified=False)
(root/'artifacts/security-cryptokit-constants-source-build.json').write_text(json.dumps(record,indent=2)+'\n');print('Built',len(r['values']),'actual native algorithm identifiers')
