#!/usr/bin/env python3
"""Run the unchanged Xcode command with the verified original LS jobs in one session."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,fcntl,hashlib,json,plistlib,runpy,subprocess
root=Path(__file__).resolve().parent.parent;parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['version','showsdks','build']);args=parser.parse_args();digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
m=runpy.run_path(str(root/'scripts/foundation-coherent-profile.py'));p=m['profile']();verified=json.loads((root/'artifacts/native-lsd-foundation-coherent-probe.json').read_text());assert verified['UTI_functional_execution_verified'] and verified['exit_status']==0
for key in ['source_runtime','source_objc','source_selector','foundation_coherent','source_fsevents']:assert verified[key]==p[key]
guest='/Volumes/SystemRoot/workspace/';build=root/'runtime/xcode-managed-services';build.mkdir(parents=True,exist_ok=True);stem='foundation-coherent-managed-xcode-'+args.mode
jobs=[]
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 for name,key in [('lsd','selected_job'),('dirhelper','paired_dirhelper_job')]:
  job=dict(verified[key]);job['StandardOutPath']=job['StandardErrorPath']=guest+'logs/'+stem+'-'+name+'.log';file=build/(stem+'-'+name+'.plist');file.write_bytes(plistlib.dumps(job));file.chmod(0o644);(root/('logs/'+stem+'-'+name+'.log')).write_text('');jobs.append(dict(name=name,path=str(file.relative_to(root)),sha256=digest(str(file.relative_to(root))),job=job))
script=build/(stem+'.sh');script.write_text('''#!/bin/bash
set -e
launchctl load /Volumes/SystemRoot/workspace/'''+jobs[1]['path']+'''
launchctl load /Volumes/SystemRoot/workspace/'''+jobs[0]['path']+'''
trap 'launchctl remove com.apple.lsd >/dev/null 2>&1; launchctl remove com.apple.bsd.dirhelper >/dev/null 2>&1' EXIT
launchctl list com.apple.lsd
/Volumes/SystemRoot/workspace/artifacts/uniform-type-identifiers-native
printf 'MANAGED_XCODE_ORIGINAL_UTI_PREFLIGHT_OK\\n'
set +e
/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild "$@"
status=$?
printf 'MANAGED_XCODE_ORIGINAL_STATUS %s\\n' "$status"
launchctl list com.apple.lsd
exit "$status"
''')
xcode_args=['-project',guest+'fixtures/XcodeSmoke/XcodeSmoke.xcodeproj','-scheme','XcodeSmoke','-sdk','macosx','-configuration','Debug','-derivedDataPath',guest+'runtime/xcode-managed-services/DerivedData','CODE_SIGNING_ALLOWED=NO','build'] if args.mode=='build' else ['-'+args.mode]
command=p['command'][:-2]+['/bin/bash',guest+str(script.relative_to(root)),*xcode_args];log='logs/'+stem+'.log'
with (root/log).open('w') as stream:r=subprocess.run(command,cwd=root,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
text=(root/log).read_text();print(text[-9000:],flush=True)
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild';assert digest(original)==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'command':command,'exit_status':r.returncode,'log':log,'log_sha256':digest(log),'jobs':jobs,'script':str(script.relative_to(root)),'script_sha256':digest(str(script.relative_to(root))),'original_xcodebuild_sha256':digest(original),'xcode_arguments':xcode_args,'UTI_preflight_verified':'MANAGED_XCODE_ORIGINAL_UTI_PREFLIGHT_OK' in text,'full_xcode_build_ready':False,'signing_ready':False}
(root/('artifacts/'+stem+'.json')).write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(r.returncode)
