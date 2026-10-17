#!/usr/bin/env python3
"""Compare source computation with original instructions and read actual guest metadata."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
subprocess.run(['python3','scripts/analyze-mobilegestalt-version.py'],cwd=root,check=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';include=root/'vendor/darling/src/libMobileGestalt/include'
sources=[('runtime/mobilegestalt-reference/reference.S','runtime/mobilegestalt-reference/reference.o'),('fixtures/hello/mobilegestalt-version-reference.m','artifacts/mobilegestalt-version-reference.o'),('fixtures/hello/mobilegestalt-version.m','artifacts/mobilegestalt-version.o')]
for src,obj in sources:subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-I'+str(include),'-fblocks','-O2','-c',src,'-o',obj],cwd=root,check=True)
symbols={line.split()[-1]:int(line.split()[0],16) for line in subprocess.check_output(['llvm-nm-19','--defined-only','runtime/mobilegestalt-reference/reference.o'],cwd=root,text=True).splitlines() if len(line.split())==3}
for name,length in [('product_version',43),('human_version',149)]:assert symbols['_reference_'+name+'_end']-symbols['_reference_'+name]==length
for name,objects,extras in [('mobilegestalt-version-reference',['artifacts/mobilegestalt-version-reference.o','runtime/mobilegestalt-reference/reference.o','runtime/mobilegestalt-source/MobileGestalt.o'],[]),('mobilegestalt-version',['artifacts/mobilegestalt-version.o'],['-L',str(root/'runtime/mobilegestalt-source/libraries'),'-lMobileGestalt'])]:
 subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-framework','Foundation','-framework','CoreFoundation','-lobjc','-lSystem',*extras,*objects,'-o','artifacts/'+name],cwd=root,check=True)
m=runpy.run_path(str(root/'scripts/mobilegestalt-source-profile.py'));p=m['profile']();results=[]
digest=lambda s:hashlib.sha256((root/s).read_bytes()).hexdigest()
for name in ['mobilegestalt-version-reference','mobilegestalt-version']:
 c=p['command'][:-2]+['/Volumes/SystemRoot/workspace/artifacts/'+name];r=subprocess.run(c,cwd=root,env=m['environment'](p),capture_output=True,text=True);log='logs/'+name+'.log';(root/log).write_text(r.stdout+r.stderr);print(r.stdout+r.stderr,end='',flush=True)
 results.append(dict(command=c,exit_status=r.returncode,log=log,log_sha256=digest(log),binary='artifacts/'+name,binary_sha256=digest('artifacts/'+name)))
 if r.returncode:break
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'results':results,'sources':{s:digest(s) for s,o in sources},'reference_analysis_sha256':digest('artifacts/mobilegestalt-version-callback-analysis.json'),'runtime_execution_verified':len(results)==2 and all(r['exit_status']==0 for r in results),'other_MobileGestalt_device_APIs_verified':False}
(root/'artifacts/mobilegestalt-source-test.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if record['runtime_execution_verified'] else 1)
