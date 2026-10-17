#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/materialize-runtime-profile.py'));p=m['profile']()
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';folder=root/'runtime/materialize-policy-tests';folder.mkdir(exist_ok=True)
source='fixtures/hello/materialize-policy.c';obj=folder/'native.o';binary=folder/'native'
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-Wno-deprecated-declarations','-O0','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','14','14','-syslibroot',str(sdk),'-lSystem',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))]
a=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True);text=a.stdout+a.stderr;log='logs/materialize-policy-native.log';(root/log).write_text(text);digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest();match=re.search(r'NATIVE_MATERIALIZE_THREAD_POLICY_ROUNDTRIP_ISOLATION_8_THREADS_512_UPDATES_ERRORS_OK checks=(\d+)',text)
d=dict(checked_at=datetime.now(timezone.utc).isoformat(),source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),command=command,exit_status=a.returncode,log=log,log_sha256=digest(log),source_materialize_policy=p['source_materialize_policy'],checks=int(match[1]) if match else 0,verified=a.returncode==0 and match is not None,full_xcode_build_ready=False)
(root/'artifacts/materialize-policy-native-test.json').write_text(json.dumps(d,indent=2)+'\n');print(text);assert d['verified']
