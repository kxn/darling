#!/usr/bin/env python3
"""Run existing process, Sandbox and C++ runtime checks in the new root."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/quarantine-vfs-runtime-profile.py'));p=m['profile'](False)
guest='/Volumes/SystemRoot/workspace/'
specs=[('generation','runtime/pid-generation-kernel-source/test-generation',[], 'PROCESS_GENERATION_LIBPROC_AUDIT_FORK_EXEC_FAILED_EXEC_STALE_TOKEN_AND_SIZE_OK'),('Sandbox','runtime/sandbox-policy-source/test',[guest+'runtime/foundation-native-library-stage/libDarlingNativeSandbox.dylib'],'checks=95'),('expected','runtime/expected-access-source/test',[],'checks=3215'),('allocator','runtime/expected-access-source/regression/default',[],'checks=251'),('replacement','runtime/expected-access-source/regression/replacements',[],'checks=331'),('crypto','runtime/coreutils-crypto-source/test',[guest+'runtime/coreutils-crypto-source/independent-vectors.bin'],'COREUTILS_SOURCE_DESCRIPTOR_ABI_HASH_HMAC_HKDF_INDEPENDENT_VECTORS_AND_GUARDS_OK')]
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest();rows=[]
for label,binary,args,marker in specs:
    command=p['command'][:-2]+[guest+binary,*args]
    if label=='expected':command=[s.replace('DYLD_LIBRARY_PATH=','DYLD_LIBRARY_PATH='+guest+'runtime/expected-access-source/fixture-libraries:',1) if s.startswith('DYLD_LIBRARY_PATH=') else s for s in command]
    log='logs/quarantine-vfs-regression-'+label+'.log'
    with (root/log).open('w') as stream:r=subprocess.run(command,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
    text=(root/log).read_text();print(label,r.returncode,text[-700:],flush=True)
    rows.append(dict(label=label,binary=binary,binary_sha256=digest(binary),log=log,log_sha256=digest(log),exit_status=r.returncode,command=command))
    assert r.returncode==0 and marker in text,(label,text)
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'checks':rows,'full_xcode_build_ready':False}
(root/'artifacts/quarantine-vfs-regression.json').write_text(json.dumps(record,indent=2)+'\n');print('Existing identity/Sandbox/exception/allocation/replacement checks pass in the new coherent root')
