#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group();group.add_argument('--eager-control',action='store_true');group.add_argument('--image4',action='store_true');args=parser.parse_args()
m=runpy.run_path(str(root/'scripts/device-identity-native-profile.py'));p=m['profile'](False)
build=root/'runtime/device-identity-native';sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';source='fixtures/hello/native-foundation-load.c';obj=build/'load.o';binary=build/'load'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-lSystem',str(obj),'-o',str(binary)],check=True)
guest=lambda path:'/Volumes/SystemRoot/workspace/'+str(path.relative_to(root));command=p['command'][:-2]+[guest(binary),'/System/Library/PrivateFrameworks/DeviceIdentity.framework/Versions/A/DeviceIdentity'];log='logs/device-identity-native-'+('eager-control-' if args.eager_control else 'image4-' if args.image4 else '')+'load.log'
if args.image4:command[-1]='/usr/lib/libimg4.dylib'
if args.eager_control:command=[a.replace('DYLD_FRAMEWORK_PATH=','DYLD_FRAMEWORK_PATH=/Volumes/SystemRoot/workspace/runtime/device-identity-native/eager-control:',1) if a.startswith('DYLD_FRAMEWORK_PATH=') else a for a in command]
with (root/log).open('w') as stream:r=subprocess.run(command,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
text=(root/log).read_text();print(text[-6000:],flush=True);digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
success=r.returncode==0 and 'NATIVE_FOUNDATION_DLOPEN_COMPLETED' in text
control_ok=args.eager_control and r.returncode!=0 and 'Symbol not found: _SecKeyCopySystemKey' in text
components={name:digest(name) for name in ['artifacts/iokit-main-port-source-build.json','artifacts/security-device-constant-build.json','artifacts/crypto-token-error-source-build.json']}
if args.eager_control:components['runtime/rebuilt-device-identity-eager-control/reconstruction.json']=digest('runtime/rebuilt-device-identity-eager-control/reconstruction.json')
record=dict(source_components=components,image4_alias_probe=args.image4,eager_binding_control=args.eager_control,expected_negative_control_verified=control_ok,checked_at=datetime.now(timezone.utc).isoformat(),stage='artifacts/device-identity-native-stage.json',stage_sha256=digest('artifacts/device-identity-native-stage.json'),runtime='artifacts/quarantine-vfs-runtime-stage.json',runtime_sha256=digest('artifacts/quarantine-vfs-runtime-stage.json'),command=command,source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(str(binary.relative_to(root))),exit_status=r.returncode,log=log,log_sha256=digest(log),native_dlopen_verified=success,device_attestation_verified=False)
(root/('artifacts/device-identity-native-'+('eager-control-' if args.eager_control else 'image4-' if args.image4 else '')+'load.json')).write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if (control_ok if args.eager_control else success) else 1)
