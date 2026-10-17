#!/usr/bin/env python3
"""Probe the actual Foundation fixture or original xcodebuild with the source kernel."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
digest=lambda s:hashlib.sha256((root/s).read_bytes()).hexdigest()
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=['foundation','version','showsdks']);args=parser.parse_args()
m=runpy.run_path(str(root/'scripts/metadata-kernel-profile.py'));p=m['profile']()
if args.mode=='foundation':command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/artifacts/coretypes-resource-values']
else:command=p['command'][:-1]+['-'+args.mode]
r=subprocess.run(command,cwd=root,env=m['environment'](p),capture_output=True,text=True)
log='logs/metadata-kernel-'+args.mode+'-probe.log';(root/log).write_text(r.stdout+r.stderr)
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
assert digest(original)==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
report={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'command':command,'exit_status':r.returncode,'log':log,'log_sha256':digest(log),'diagnostic':r.stdout+r.stderr,'original_xcodebuild_sha256':digest(original),'full_xcode_build_ready':False,'signing_ready':False}
if args.mode=='foundation':report.update(fixture_source_sha256=digest('fixtures/hello/coretypes-resource-values.m'),fixture_binary_sha256=digest('artifacts/coretypes-resource-values'),Foundation_metadata_fixture_passed=r.returncode==0 and 'directory=1 attributes=1 enumeration=3 errors=0' in r.stdout)
(root/('artifacts/metadata-kernel-'+args.mode+'-probe.json')).write_text(json.dumps(report,indent=2)+'\n')
print(r.stdout+r.stderr,end='');raise SystemExit(r.returncode)
