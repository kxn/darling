#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/sandbox-check-source-profile.py'));p=m['profile'](False)
build=root/'runtime/sandbox-check-source';sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';guest=root/'runtime/rootfs/usr/libexec/darling'
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
flags=['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-c']
capture_dir=build/'capture-libraries';capture_dir.mkdir(exist_ok=True)
capture=capture_dir/'libSandboxCheckCapture.dylib';obj=build/'capture.o'
subprocess.run([*flags,'fixtures/hello/sandbox-check-capture.c','-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(guest),'-L'+str(guest/'usr/lib'),'-lSystem','-install_name','/usr/lib/libSandboxCheckCapture.dylib',str(obj),'-o',str(capture)],check=True)
rows=[];native='runtime/foundation-native-library-stage/libDarlingNativeSandbox.dylib'
for mode in ['capture','real']:
    obj=build/('test-'+mode+'.o');binary=build/('test-'+mode)
    subprocess.run([*flags,*(['-DCAPTURE_TEST'] if mode=='capture' else []),'fixtures/hello/sandbox-check-source.c','-o',str(obj)],check=True)
    subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(guest),'-L'+str(capture_dir),*(['-lSandboxCheckCapture'] if mode=='capture' else []),'-L'+str(guest/'usr/lib'),'-lSystem',str(obj),'-o',str(binary)],check=True)
    command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root)),'/Volumes/SystemRoot/workspace/'+native]
    if mode=='capture':command=[arg.replace('DYLD_LIBRARY_PATH=','DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/sandbox-check-source/capture-libraries:',1) if arg.startswith('DYLD_LIBRARY_PATH=') else arg for arg in command]
    log='logs/sandbox-check-source-'+mode+'.log'
    with (root/log).open('w') as stream:r=subprocess.run(command,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
    print(mode,r.returncode,(root/log).read_text()[-2500:],flush=True)
    rows.append({'mode':mode,'command':command,'exit_status':r.returncode,'log':log,'log_sha256':digest(log),'binary':str(binary.relative_to(root)),'binary_sha256':digest(str(binary.relative_to(root)))})
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'checks':rows,'sources':{n:digest(n) for n in ['fixtures/hello/sandbox-check-source.c','fixtures/hello/sandbox-check-capture.c']},'native':native,'native_sha256':digest(native),'capture_helper':str(capture.relative_to(root)),'capture_helper_sha256':digest(str(capture.relative_to(root))),'capture_is_test_only':True,'approval_policy_execution_verified':False,'full_xcode_build_ready':False}
(root/'artifacts/sandbox-check-source-test.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if all(c['exit_status']==0 for c in rows) else 1)
