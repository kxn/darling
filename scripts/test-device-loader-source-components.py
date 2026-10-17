#!/usr/bin/env python3
"""Exercise real IOKit IPC and the native-valued constant objects."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent;m=runpy.run_path(str(root/'scripts/device-identity-native-profile.py'));p=m['profile'](False)
build=root/'runtime/device-loader-source-components';build.mkdir(exist_ok=True);sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';source='fixtures/hello/device-loader-source-components.c';obj=build/'test.o';binary=build/'test'
subprocess.run(['clang-19','-target','x86_64-apple-macos12','-isysroot',str(sdk),'-Wno-deprecated-declarations','-O2','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','12','12','-syslibroot',str(sdk),'-L'+str(root/'runtime/foundation-native-library-stage'),'-F'+str(root/'runtime/iokit-main-port-source/frameworks'),'-framework','IOKit','-framework','CoreFoundation','-lSystem',str(obj),'-o',str(binary)],check=True)
guest=lambda path:'/Volumes/SystemRoot/workspace/'+str(path.relative_to(root));command=p['command'][:-2]+[guest(binary)];log='logs/device-loader-source-components-test.log'
with (root/log).open('w') as stream:r=subprocess.run(command,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
text=(root/log).read_text();print(text[-5000:],flush=True);digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest();success=r.returncode==0 and 'DEVICE_LOADER_ACTUAL_IOKIT_BACKEND_PORT_ERRORS_MATCHING_AND_NATIVE_SECURITY_TOKEN_CONSTANTS_OK' in text
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(str(binary.relative_to(root))),command=command,log=log,log_sha256=digest(log),exit_status=r.returncode,IOKit_source_report='artifacts/iokit-main-port-source-build.json',IOKit_source_report_sha256=digest('artifacts/iokit-main-port-source-build.json'),Security_constant_report='artifacts/security-device-constant-build.json',Security_constant_report_sha256=digest('artifacts/security-device-constant-build.json'),token_constant_report='artifacts/crypto-token-error-source-build.json',token_constant_report_sha256=digest('artifacts/crypto-token-error-source-build.json'),real_backend_forwarding_and_constant_values_verified=success,hardware_attestation_verified=False)
(root/'artifacts/device-loader-source-components-test.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if success else 1)
