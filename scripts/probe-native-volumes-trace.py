#!/usr/bin/env python3
"""Diagnose the real mounted-volume API used during file-coordination startup."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess,time
root=Path(__file__).resolve().parent.parent;m=runpy.run_path(str(root/'scripts/commoncrypto-original-profile.py'));p=m['profile']()
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';build=root/'runtime/native-volumes';build.mkdir(exist_ok=True);source='fixtures/hello/native-volumes.m';obj=build/'test.o';binary=build/'test'
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-Wno-deprecated-declarations','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','14','14','-syslibroot',str(sdk),'-lSystem','-lobjc','-framework','Foundation',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))]
command[3]='20'
log='logs/native-volumes-trace-probe.log'
with (root/log).open('w') as stream:
    process=subprocess.Popen(command,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
    deadline=time.monotonic()+12
    while process.poll() is None and time.monotonic()<deadline:
        if 'CF_MOUNT_ENUMERATOR 0x' in (root/log).read_text():
            trace=subprocess.run(['python3','scripts/capture-darling-stacks.py','--stem','native-volumes-next-stacks','--match','/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))],capture_output=True,text=True)
            (root/'logs/native-volumes-next-stacks-driver.log').write_text(trace.stdout+trace.stderr)
            if not trace.returncode:subprocess.run(['python3','scripts/annotate-macho-stack.py','--stem','native-volumes-next-stacks','--runtime-root','runtime/xpc-sent-message-source/darling-root'],check=True)
            break
        time.sleep(.05)
    status=process.wait()
text=(root/log).read_text();digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),command=command,exit_status=status,log=log,log_sha256=digest(log),source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),probe_returned='NATIVE_VOLUMES_PROBE_RETURNED' in text,filecoordination_service_verified=False)
(root/'artifacts/native-volumes-trace-probe.json').write_text(json.dumps(record,indent=2)+'\n');print(status,text)
