#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/mdns-native-profile.py'));p=m['profile'](include_system_resources=False)
config=json.loads((root/'config/security-out-of-band-values.json').read_text());build=root/'runtime/security-out-of-band-values';rows=[]
for name,layout in config['classes'].items():
    for ivar in layout['ivars']:rows.append('{'+json.dumps(name)+','+str(layout['instance_size'])+','+json.dumps(ivar['name'])+','+str(ivar['offset'])+'}')
(build/'native-layouts.h').write_text('static const struct {const char *name;size_t size;const char *ivar;size_t offset;} layouts[]={'+','.join(rows)+'};\n')
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';obj=build/'test.o';binary=build/'test';digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-I'+str(root/'vendor/darling/src/external/security/OSX/sec/Security'),'-I'+str(build),'-fobjc-arc','-O2','-c','fixtures/hello/security-out-of-band-values.m','-o',str(obj)],cwd=root,check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','14','14','-syslibroot',str(sdk),'-L'+str(build),'-lDarlingSecurityOutOfBandValues','-framework','Foundation','-framework','CoreFoundation','-lobjc','-lSystem',str(obj),'-o',str(binary)],cwd=root,check=True)
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))];log='logs/security-out-of-band-values-test.log'
with (root/log).open('w') as stream:r=subprocess.run(command,cwd=root,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
text=(root/log).read_text();print(text[-4500:]);verified=r.returncode==0 and 'APPLE_SECURITY_OOB_VALUES_LAYOUT_RETAIN_SECURE_ARCHIVE_AND_REJECTION_OK' in text
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'command':command,'exit_status':r.returncode,'log':log,'log_sha256':digest(log),'source':'fixtures/hello/security-out-of-band-values.m','source_sha256':digest('fixtures/hello/security-out-of-band-values.m'),'binary':str(binary.relative_to(root)),'binary_sha256':digest(str(binary.relative_to(root))),'value_class_execution_verified':verified,'strict_declared_field_type_enforcement_verified':False,'numeric_primitive_observation_retained':True,'cloud_keychain_RPC_execution_verified':False,'full_xcode_build_ready':False}
(root/'artifacts/security-out-of-band-values-test.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if verified else 1)
