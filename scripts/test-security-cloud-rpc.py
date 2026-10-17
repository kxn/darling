#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('modes',nargs='*',default=['configuration','local','unavailable','roundtrip']);parser.add_argument('--typed-new-delete',action='store_true');args=parser.parse_args()
m=runpy.run_path(str(root/('scripts/typed-new-delete-profile.py' if args.typed_new_delete else 'scripts/security-cloud-rpc-profile.py')));p=m['profile'](include_system_resources=False)
stem='security-current-item' if args.typed_new_delete else 'security-cloud-rpc'
build=root/'runtime/security-cloud-rpc';sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
flags=p['source_security_cloud_rpc']['build']['compiler_namespace_flags']
layout=p['source_security_cloud_rpc']['build']['native_result_layout'];ivars={v['name']:v['offset'] for v in layout['ivars']}
(build/'native-current-item-layout.h').write_text('static const unsigned native_current_item_size='+str(layout['instance_size'])+', native_current_item_ref_offset='+str(ivars['_persistentRef'])+', native_current_item_date_offset='+str(ivars['_currentItemPointerModificationTime'])+';\n')
source='fixtures/hello/security-cloud-rpc.m';obj=build/'test.o';binary=build/'test'
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-I'+str(build/'include'),'-I'+str(build),'-I'+str(root/'vendor/darling/src/external/security/OSX/sec/Security'),*flags,'-fobjc-arc','-O2','-c',source,'-o',str(obj)],cwd=root,check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','14','14','-syslibroot',str(sdk),'-F'+str(root/'runtime/security-cloud-rpc-stage/frameworks'),'-framework','Security','-framework','Foundation','-framework','CoreFoundation','-L'+str(build),'-lDarlingSecurityCloudRPC','-L'+str(root/'runtime/security-out-of-band-values'),'-lDarlingSecurityOutOfBandValues','-lobjc','-lSystem',str(obj),'-o',str(binary)],check=True)
rows=[]
for mode in args.modes:
    assert mode in ['configuration','local','unavailable','roundtrip']
    command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root)),mode];log='logs/'+stem+'-'+mode+'.log'
    with (root/log).open('w') as stream:r=subprocess.run(command,cwd=root,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
    text=(root/log).read_text();print(mode,r.returncode,text[-3800:],flush=True)
    rows.append({'mode':mode,'command':command,'exit_status':r.returncode,'log':log,'log_sha256':digest(log)})
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'source':source,'source_sha256':digest(source),'binary':str(binary.relative_to(root)),'binary_sha256':digest(str(binary.relative_to(root))),'checks':rows,'cloud_backend_execution_verified':False,'full_xcode_build_ready':False}
(root/('artifacts/'+stem+'-test.json')).write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if all(c['exit_status']==0 for c in rows) else 1)
