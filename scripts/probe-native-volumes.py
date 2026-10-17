#!/usr/bin/env python3
"""Diagnose the real mounted-volume API used during file-coordination startup."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent;m=runpy.run_path(str(root/'scripts/commoncrypto-original-profile.py'));p=m['profile']()
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';build=root/'runtime/native-volumes';build.mkdir(exist_ok=True);source='fixtures/hello/native-volumes.m';obj=build/'test.o';binary=build/'test'
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-Wno-deprecated-declarations','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','14','14','-syslibroot',str(sdk),'-lSystem','-lobjc','-framework','Foundation',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))];r=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True);text=r.stdout+r.stderr;log='logs/native-volumes-probe.log';(root/log).write_text(text);digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),command=command,exit_status=r.returncode,log=log,log_sha256=digest(log),source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),probe_returned='NATIVE_VOLUMES_PROBE_RETURNED' in text,filecoordination_service_verified=False)
(root/'artifacts/native-volumes-probe.json').write_text(json.dumps(record,indent=2)+'\n');print(r.returncode,text)
