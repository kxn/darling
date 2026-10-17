#!/usr/bin/env python3
"""Verify real private bind/tmpfs mount names, escaping and guest-root boundaries."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,shlex,subprocess
root=Path(__file__).resolve().parent.parent
work=root/'runtime/mount-fixture';work.mkdir(exist_ok=True)
for n in ['source','space mount','mount-prefix','mount-prefix-two']:(work/n).mkdir(exist_ok=True)
(work/'source/no-read').touch();(work/'source/no-read').chmod(0)
(work/'source/deleted-test').unlink(missing_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';guest=root/'runtime/rootfs/usr/libexec/darling'
commands=[['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-c','fixtures/hello/mount-path-kernel.c','-o','artifacts/mount-path-kernel.o'],['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(guest),'-L',str(root/'runtime/mount-path-kernel-source'),'-lsystem_kernel','-lSystem','artifacts/mount-path-kernel.o','-o','artifacts/mount-path-kernel']]
for c in commands:subprocess.run(c,cwd=root,check=True)
m=runpy.run_path(str(root/'scripts/mount-path-kernel-profile.py'));p=m['profile']()
env=[a for a in p['command'] if a.startswith(('DYLD_LIBRARY_PATH=','DYLD_FRAMEWORK_PATH=','OBJC_DISABLE_TAGGED_POINTERS='))]
script=root/'runtime/mount-fixture/session.sh'
script.write_text('''#!/bin/bash
set -euo pipefail
mount --bind /workspace/runtime/mount-fixture/source '/workspace/runtime/mount-fixture/space mount'
mount -t tmpfs -o mode=755 tmpfs /workspace/runtime/mount-fixture/mount-prefix
mkdir -p /state/prefix-mount-test-neighbor
mount -t tmpfs -o mode=755 tmpfs /state/prefix-mount-test-neighbor
trap '/usr/bin/darling shutdown >/dev/null 2>&1' EXIT
'''+shlex.join(['/usr/bin/darling','shell','/usr/bin/env',*env,'/Volumes/SystemRoot/workspace/artifacts/mount-path-kernel'])+'\n')
host_mounts_before=Path('/proc/self/mountinfo').read_bytes()
command=['timeout','-k','5','60','bin/darling','--linux','/bin/bash','/workspace/runtime/mount-fixture/session.sh']
r=subprocess.run(command,cwd=root,env=m['environment'](p),capture_output=True,text=True)
host_mounts_after=Path('/proc/self/mountinfo').read_bytes()
assert host_mounts_before==host_mounts_after, 'Host mount namespace changed during the private fixture'
log='logs/mount-path-kernel-test.log';(root/log).write_text(r.stdout+r.stderr);digest=lambda s:hashlib.sha256((root/s).read_bytes()).hexdigest()
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'command':command,'exit_status':r.returncode,'log':log,'log_sha256':digest(log),'diagnostic':r.stdout+r.stderr,'source_sha256':digest('fixtures/hello/mount-path-kernel.c'),'binary_sha256':digest('artifacts/mount-path-kernel'),'session_script_sha256':digest('runtime/mount-fixture/session.sh'),'runtime_execution_verified':r.returncode==0 and 'MOUNT_PATH_KERNEL_PASS' in r.stdout,'host_mounts_changed':host_mounts_before!=host_mounts_after,'host_mountinfo_before_sha256':hashlib.sha256(host_mounts_before).hexdigest(),'host_mountinfo_after_sha256':hashlib.sha256(host_mounts_after).hexdigest()}
(root/'artifacts/mount-path-kernel-test.json').write_text(json.dumps(record,indent=2)+'\n');print(r.stdout+r.stderr,end='');raise SystemExit(r.returncode)
