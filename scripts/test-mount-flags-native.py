#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent;m=runpy.run_path(str(root/'scripts/mount-flags-runtime-profile.py'));p=m['profile']()
folder=root/'runtime/mount-flags-tests';folder.mkdir(exist_ok=True);sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';source='fixtures/hello/mount-flags.c';binary=folder/'native';obj=folder/'native.o'
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-O0','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','14','14','-syslibroot',str(sdk),'-lSystem','-undefined','dynamic_lookup',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))];a=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True);text=a.stdout+a.stderr
log='logs/mount-flags-native.log';(root/log).write_text(text);digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest();match=re.search(r'NATIVE_MOUNT_FLAGS_LINUX_TRANSLATION_OK checks=(\d+) mounts=(\d+)',text)
d=dict(checked_at=datetime.now(timezone.utc).isoformat(),command=command,exit_status=a.returncode,source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),log=log,log_sha256=digest(log),checks=int(match[1]) if match else 0,mounts=int(match[2]) if match else 0,source_mount_flags=p['source_mount_flags'],runtime_execution_verified=a.returncode==0 and match is not None,full_xcode_build_ready=False)
(root/'artifacts/mount-flags-native-test.json').write_text(json.dumps(d,indent=2)+'\n');print(text);assert d['runtime_execution_verified']
