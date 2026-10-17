#!/usr/bin/env python3
"""Observe original CarbonCore/CF/Foundation volume enumeration on the source runtime."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, runpy, subprocess
root=Path(__file__).resolve().parent.parent
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
assert digest('runtime/rebuilt-carboncore-native/CarbonCore')=='4ccae193c819a25b4578fbff9d84d918ff19c097a727a5f6e4f6b44d8bfc1f2c'
m=runpy.run_path(str(root/'scripts/mount-flags-runtime-profile.py'));p=m['profile']()
folder=root/'runtime/mount-volume-probe';folder.mkdir(exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
source='fixtures/hello/fileidtree-root.m';obj=folder/'native.o';binary=folder/'native'
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-Wno-deprecated-declarations','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','14','14','-syslibroot',str(sdk),'-lSystem','-lobjc','-framework','Foundation',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))]
a=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True)
text=a.stdout+a.stderr;log='logs/mount-volumes-native.log';(root/log).write_text(text)
match=re.search(r'FILEIDTREE_MOUNT_POINTS status=(-?\d+) count=(\d+)',text)
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),command=command,exit_status=a.returncode,
 source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),
 log=log,log_sha256=digest(log),source_mount_flags=p['source_mount_flags'],
 probe_returned='NATIVE_VOLUMES_PROBE_RETURNED' in text,
 fileidtree_status=int(match[1]) if match else None,fileidtree_volume_count=int(match[2]) if match else None,
 original_coreservicesd_loaded=False,full_xcode_build_ready=False)
(root/'artifacts/mount-volumes-native-probe.json').write_text(json.dumps(record,indent=2)+'\n')
print(text);assert a.returncode==0 and record['probe_returned']
