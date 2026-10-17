#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,runpy
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/native-log-message-profile.py'));environment=m['environment']
def profile():
 stage=json.loads((root/'artifacts/log-hooks-stage.json').read_text());build=stage['source_build']
 override=os.environ.get('LINUXCODE_LIBTRACE_BUILD_REPORT')
 if override:
  report=(root/override).resolve();assert report.is_relative_to(root/'artifacts')
  build=json.loads(report.read_text());assert build['full_libtrace_source_build'] and build['complete_source_files']==9
 p=m['profile'](source_build=build)
 for key in ['base','library']:assert hashlib.sha256((root/stage[key]).read_bytes()).hexdigest()==stage[key+'_sha256']
 c=list(p['command']);i=next(i for i,v in enumerate(c) if v.startswith('DYLD_LIBRARY_PATH='));c[i]='DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/log-hooks/libraries:'+c[i].split('=',1)[1]
 return {**p,'command':c,'source_libtrace':build,'log_hooks':stage}
