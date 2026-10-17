#!/usr/bin/env python3
"""Compare Darwin quota errors against the real Linux filesystem backend."""
from pathlib import Path
from datetime import datetime,timezone
import ctypes,errno,hashlib,json,os,runpy,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/quarantine-vfs-runtime-profile.py'));p=m['profile'](False)
linux=ctypes.CDLL(None,use_errno=True);linux.syscall.restype=ctypes.c_long
fd=os.open(root,os.O_PATH|os.O_CLOEXEC);buffer=ctypes.create_string_buffer(80);reference=[]
try:
    for operation in [0x800007,0x800004]:
        for kind in [0,1]:
            ctypes.set_errno(0);result=linux.syscall(ctypes.c_long(443),ctypes.c_int(fd),ctypes.c_uint((operation<<8)|kind),ctypes.c_uint(0),ctypes.byref(buffer))
            reference.append(dict(operation=operation,type=kind,result=result,Linux_errno=ctypes.get_errno()))
finally:os.close(fd)
assert all(row['result']==-1 and row['Linux_errno'] in [errno.ENOSYS,errno.EOPNOTSUPP] for row in reference),'This test specifically covers a real quota-unsupported filesystem; it must not invent a positive quota result.'
build=root/'runtime/quarantine-vfs-test';sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';source='fixtures/hello/quotactl-source.c';obj=build/'quota.o';binary=build/'quota'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-lSystem',str(obj),'-o',str(binary)],check=True)
guest=lambda path:'/Volumes/SystemRoot/workspace/'+str(path.relative_to(root));command=p['command'][:-2]+[guest(binary),'/Volumes/SystemRoot/workspace','102'];log='logs/quotactl-source-test.log'
with (root/log).open('w') as stream:r=subprocess.run(command,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
text=(root/log).read_text();print(text,flush=True);digest=lambda path:hashlib.sha256((root/path).read_bytes()).hexdigest()
success=r.returncode==0 and 'QUOTACTL_SOURCE_REAL_LINUX_BACKEND_UNSUPPORTED_FILESYSTEM_AND_ERRORS_OK' in text
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),runtime_stage='artifacts/quarantine-vfs-runtime-stage.json',runtime_stage_sha256=digest('artifacts/quarantine-vfs-runtime-stage.json'),source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(str(binary.relative_to(root))),Linux_reference=reference,command=command,exit_status=r.returncode,log=log,log_sha256=digest(log),unsupported_filesystem_and_error_paths_verified=success,quota_enabled_filesystem_verified=False,quota_mutations_implemented=False)
(root/'artifacts/quotactl-source-test.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if success else 1)
