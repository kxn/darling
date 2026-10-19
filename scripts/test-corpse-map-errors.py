#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/corpse-map-runtime-profile.py'));p=m['profile']()
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
build=root/'runtime/corpse-map-tests';build.mkdir(exist_ok=True);obj=build/'errors.o';binary=build/'errors'
source='fixtures/hello/corpse-map-errors.c'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-Wno-deprecated-declarations','-c',source,'-o',str(obj)],cwd=root,check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-lSystem',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))]
log='logs/corpse-map-native-errors.log'
with (root/log).open('w') as stream:r=subprocess.run(command,env=m['environment'](p),cwd=root,stdout=stream,stderr=subprocess.STDOUT)
text=(root/log).read_text();print(text[-4000:],end='');digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),source_runtime=p['source_runtime'],source_corpse_map_errors=p['source_corpse_map_errors'],log=log,log_sha256=digest(log),command=command,exit_status=r.returncode,
    verified=r.returncode==0 and 'CORPSE_MAP_LIVE_TASK_ERRORS_AND_SERVER_SURVIVAL_OK' in text,checks=[int(n) for n in re.findall(r'checks=(\d+)',text)],real_corpse_kcdata_mapping_implemented=False)
(root/'artifacts/corpse-map-native-errors.json').write_text(json.dumps(record,indent=2)+'\n')
raise SystemExit(0 if record['verified'] else 1)
