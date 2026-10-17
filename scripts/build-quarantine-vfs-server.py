#!/usr/bin/env python3
"""Build and privately select the real registered-process Sandbox query server."""
from pathlib import Path
import fcntl,hashlib,json,runpy,shutil,subprocess
root=Path(__file__).resolve().parent.parent
p=runpy.run_path(str(root/'scripts/crypto-quarantine-runtime-profile.py'))['profile']()
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
base='runtime/darlingserver-source-build/darlingserver/darlingserver';build=root/'runtime/quarantine-vfs-server';build.mkdir(exist_ok=True);target=build/'darlingserver'
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    # Older validated profiles still reference this build output. Preserve it
    # and force a real relink, then publish the new server in its own directory.
    backup=build/'baseline-build-output';shutil.copy2(root/base,backup);baseline_sha=digest(base)
    try:
        (root/base).unlink()
        subprocess.run(['cmake','--build',str(root/'runtime/darlingserver-source-build'),'--target','darlingserver','-j','8'],check=True)
        compiled_sha=digest(base);pending=target.with_suffix('.pending');shutil.copy2(root/base,pending);pending.replace(target)
    finally:
        restored=(root/base).with_suffix('.restore');shutil.copy2(backup,restored);restored.replace(root/base)
    assert digest(base)==baseline_sha
files=['vendor/darlingserver/'+n for n in ['src/call.cpp','src/process.cpp','internal-include/darlingserver/process.hpp','duct-tape/src/task.c','duct-tape/include/darlingserver/duct-tape.h','scripts/generate-rpc-wrappers.py']]
selected={k:dict(v) for k,v in p['source_runtime'].items()};selected['LINUXCODE_DARLING_SERVER']={'path':str(target.relative_to(root)),'sha256':digest(str(target.relative_to(root)))}
report={'server':str(target.relative_to(root)),'server_sha256':digest(str(target.relative_to(root))),'compilation_output_path':base,'compilation_output_before_restore_sha256':compiled_sha,'baseline_build_output_restored':True,'baseline_build_output_sha256':baseline_sha,'source_files':{n:digest(n) for n in files},'source_runtime':selected,'previous_source_runtime':p['source_runtime'],'source_commit':subprocess.check_output(['git','-C',str(root/'vendor/darlingserver'),'rev-parse','HEAD'],text=True).strip(),'query_uses_registered_process_and_confinement_state':True,'audit_PID_version_uses_fork_exec_counter':True,'unsupported_POSIX_query_flags_return_ENOTSUP':True,'profile_application_implemented':False,'sandbox_approval_grants_implemented':False,'Quarantine_flags_6_requires_source_VFS':True,'runtime_execution_verified':False,'full_xcode_build_ready':False}
(root/'artifacts/quarantine-vfs-server-build.json').write_text(json.dumps(report,indent=2)+'\n');print('Selected source server with registered-process unconfined query state and real audit generations; no profile/approval grants')
