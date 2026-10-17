#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
subprocess.run(['python3','scripts/analyze-runnable-archs.py'],cwd=root,check=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';build=root/'runtime/runnable-archs-reference'
common=['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-fblocks','-O2']
inputs=[('vendor/darling/src/external/dyld/src/runnable_archs.c','source.o',['-Ivendor/darling/src/external/dyld/include','-include','fixtures/hello/runnable-archs-redirect.h']),('runtime/runnable-archs-reference/reference.S','reference.o',[]),('fixtures/hello/runnable-archs.c','test.o',[])]
for src,obj,extra in inputs:subprocess.run([*common,*extra,'-c',src,'-o',str(build/obj)],cwd=root,check=True)
symbols={v.split()[-1]:int(v.split()[0],16) for v in subprocess.check_output(['llvm-nm-19','--defined-only',str(build/'reference.o')],text=True).splitlines() if len(v.split())==3}
for name,n in [('reference_for_each_runnable_arch_name',182),('reference_has_file',147)]:assert symbols['_'+name+'_end']-symbols['_'+name]==n
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-lSystem',*[str(build/obj) for _,obj,_ in inputs],'-o','artifacts/runnable-archs'],cwd=root,check=True)
m=runpy.run_path(str(root/'scripts/runnable-archs-profile.py'));p=m['profile']();c=p['command'][:-2]+['/Volumes/SystemRoot/workspace/artifacts/runnable-archs'];r=subprocess.run(c,cwd=root,env=m['environment'](p),capture_output=True,text=True)
log='logs/runnable-archs-test.log';(root/log).write_text(r.stdout+r.stderr);print(r.stdout+r.stderr,end='');digest=lambda s:hashlib.sha256((root/s).read_bytes()).hexdigest()
verified=r.returncode==0 and 'RUNNABLE_ARCHS_DIFFERENTIAL_CASES 788' in r.stdout and 'SOURCE_RUNNABLE_ARCHS_REAL_LIBDYLD_OWNER_AND_GUEST_NO_CACHE_FALLBACK_OK' in r.stdout
report={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'command':c,'exit_status':r.returncode,'log':log,'log_sha256':digest(log),'runtime_execution_verified':verified,'differential_cases':788 if verified else 0,'native_analysis_sha256':digest('artifacts/runnable-archs-native-analysis.json'),'source_sha256':digest('fixtures/hello/runnable-archs.c'),'redirect_header_sha256':digest('fixtures/hello/runnable-archs-redirect.h'),'binary_sha256':digest('artifacts/runnable-archs'),'arm_execution_support_added':False}
(root/'artifacts/runnable-archs-source-test.json').write_text(json.dumps(report,indent=2)+'\n');raise SystemExit(0 if verified else r.returncode or 1)
