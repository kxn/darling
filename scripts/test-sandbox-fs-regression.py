#!/usr/bin/env python3
"""Verify process identity, Quarantine side effects, XPC and original Xcode."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,runpy,shutil,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/sandbox-fs-runtime-profile.py'));p=m['profile']()
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
guest='/Volumes/SystemRoot/workspace/'
policies=json.loads((root/'artifacts/native-sandbox-policy-corpus.json').read_text())
output=root/'runtime/sandbox-fs-quarantine-output'
if output.exists():shutil.rmtree(output)
output.mkdir()
cases=[('generation',['runtime/pid-generation-kernel-source/test-generation'],'PROCESS_GENERATION_LIBPROC_AUDIT_FORK_EXEC_FAILED_EXEC_STALE_TOKEN_AND_SIZE_OK'),
       ('xpc',['runtime/xpc-loopback-sent-test/test'],'XPC_REAL_16_LOOPBACK_CHECKINS_256_REPLY_PAYLOADS_AND_CANCELLATION_OK'),
       ('native-upload',['runtime/sandbox-policy-upload/test',*[item['binary'] for item in policies['policies'].values()]],'SANDBOX_UPLOAD_NATIVE_ABI_AND_ATOMIC_FAILURE_OK checks=216 uploads=29'),
       ('quarantine',['runtime/quarantine-vfs-test/test',str(output.relative_to(root)),'runtime/quarantine-vfs-test/leaf','source'],'QUARANTINE_VFS_REAL_PERSISTED_LABELS_KERNEL_PAIRING_FORK_EXEC_AND_UNCONFINED_CONTROL_OK'),
       ('xcode-version',[],'Xcode 26.6'),('xcode-showsdks',[],'SERVICE_RUNTIME_XCODE_STATUS 0')]
rows=[];inputs={}
for name,argv,marker in cases:
    if name=='xcode-showsdks':
        command=['python3',str(root/'scripts/probe-xcode-service-runtime.py'),'--sandbox-fs','--cfprefsd-daemon','--timeout-seconds','40','showsdks']
        r=subprocess.run(command,capture_output=True,text=True)
    else:
        if name=='xcode-version':arguments=['/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild','-version']
        else:
            arguments=[guest+arg if (root/arg).exists() else arg for arg in argv]
            for arg in argv:
                if (root/arg).is_file():inputs[arg]=digest(arg)
        command=p['command'][:-2]+arguments;command[3]='40'
        r=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True)
    text=r.stdout+r.stderr;log='logs/sandbox-fs-regression-'+name+'.log';(root/log).write_text(text)
    verified=r.returncode==0 and marker in text
    rows.append(dict(name=name,command=command,exit_status=r.returncode,verified=verified,marker=marker,log=log,log_sha256=digest(log)))
    print(name,r.returncode,'verified',verified,text[-1400:],flush=True)
labels={}
if next(row for row in rows if row['name']=='quarantine')['verified']:
    for name in ['new','existing','directory','renamed','fork-inherited','exec-inherited']:
        labels[name]=os.getxattr(output/name,'user.com.apple.quarantine').decode()
    assert labels['new'].startswith('0082;') and labels['directory'].startswith('0086;00000000;') and labels['renamed'].startswith('0082;')
    assert os.getxattr(output/'new','user.user.com.apple.quarantine')==b'shadow'
    assert 'user.com.apple.quarantine' not in os.listxattr(output/'parent-unconfined-exec')
    assert 'user.com.apple.quarantine' not in os.listxattr(output/'hard-link')
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),checks=rows,source_sandbox_fs=p['source_sandbox_fs'],
            binary_inputs=inputs,physical_quarantine_labels=labels,
            runtime_execution_verified=all(row['verified'] for row in rows) and bool(labels),
            profile_application_implemented=False,full_xcode_build_ready=False)
(root/'artifacts/sandbox-fs-regression.json').write_text(json.dumps(record,indent=2)+'\n')
assert record['runtime_execution_verified']
