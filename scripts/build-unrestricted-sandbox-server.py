#!/usr/bin/env python3
"""Build a private server supporting only provably unrestricted profiles."""
from pathlib import Path
from datetime import datetime,timezone
import fcntl,hashlib,json,runpy,shutil,subprocess
root=Path(__file__).resolve().parent.parent
p=runpy.run_path(str(root/'scripts/sandbox-fs-runtime-profile.py'))['profile']()
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
build=root/'runtime/unrestricted-sandbox-server';build.mkdir(exist_ok=True)
base=root/'runtime/darlingserver-source-build/darlingserver/darlingserver'
baseline='ae78babd377dd542788f321752b11e9dea6413ee49d1009f00df825fdd9efd6b'
command=['cmake','--build',str(root/'runtime/darlingserver-source-build'),'--target','darlingserver','-j','8']
log='logs/unrestricted-sandbox-server-build.log'
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);assert digest(base)==baseline
    backup=build/'baseline-build-output';shutil.copy2(base,backup)
    try:
        base.unlink()
        with (root/log).open('w') as stream:subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,check=True)
        target=build/'darlingserver';shutil.copy2(base,target)
    finally:
        restored=base.with_suffix('.restore');shutil.copy2(backup,restored);restored.replace(base)
    assert digest(base)==baseline
files=['vendor/darlingserver/'+name for name in ['CMakeLists.txt','src/call.cpp','src/process.cpp','internal-include/darlingserver/process.hpp',
       'src/sandbox-policy.cpp','internal-include/darlingserver/sandbox-policy.hpp','src/sandbox-operation-names.inc',
       'duct-tape/src/task.c','duct-tape/include/darlingserver/duct-tape.h','scripts/generate-rpc-wrappers.py']]
selected={key:dict(item) for key,item in p['source_runtime'].items()}
selected['LINUXCODE_DARLING_SERVER']=dict(path=str(target.relative_to(root)),sha256=digest(target))
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),server=str(target.relative_to(root)),server_sha256=digest(target),
            command=command,log=log,log_sha256=digest(log),source_files={name:digest(name) for name in files},
            previous_source_runtime=p['source_runtime'],source_runtime=selected,baseline_build_output_restored=True,
            baseline_build_output_sha256=baseline,unrestricted_profile_application_implemented=True,
            restrictive_profile_application_implemented=False,profile_fork_exec_inheritance_implemented=True,
            runtime_execution_verified=False,full_xcode_build_ready=False)
(root/'artifacts/unrestricted-sandbox-server-build.json').write_text(json.dumps(report,indent=2)+'\n')
print('Built unrestricted-profile server; shared baseline restored; restrictive application still refused')
