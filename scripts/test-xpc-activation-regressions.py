#!/usr/bin/env python3
"""Existing real XPC conversations and connection/shared-memory lifetime tests."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,runpy,struct,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/xpc-activation-runtime-profile.py'));p=m['profile']();digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
data=(root/'runtime/xpc-activation-source/libxpc.dylib').read_bytes();at=32;uuid=None
for _ in range(struct.unpack_from('<I',data,16)[0]):
 cmd,size=struct.unpack_from('<II',data,at)
 if cmd==0x1b:uuid=data[at+8:at+24].hex();break
 at+=size
assert uuid
tests=[('loopback','runtime/xpc-loopback-sent-test/test','artifacts/xpc-loopback-sent-fixed.json','binary_sha256',[],['XPC_REAL_16_LOOPBACK_CHECKINS_256_REPLY_PAYLOADS_AND_CANCELLATION_OK']),
 ('connection','artifacts/xpc-connection-source','artifacts/xpc-connection-source.json','test_binary_sha256',['/usr/lib/system/libxpc.dylib',uuid],['SOURCE_XPC_8_CONCURRENT_READERS_OBSERVE_REAL_INVALIDATION_AND_32_OWNED_REASON_LIFECYCLES_OK','SOURCE_XPC_PEER_SIGNING_REQUIREMENT_RETURNS_UNSUPPORTED_WITHOUT_CONNECTION_MUTATION_OK']),
 ('shmem','artifacts/xpc-shmem-source','artifacts/libxpc-source.json','test_binary_sha256',[uuid],['XPC_SHMEM_SOURCE_32_CYCLES_COPY_RIGHTS_PAGE_ROUNDING_ALIAS_READONLY_AND_WRONG_TYPES_OK','XPC_SHMEM_SOURCE_96_KERNEL_DELIVERED_MALFORMED_LENGTHS_AND_TRUNCATION_NO_RIGHT_LEAK_OK','XPC_SHMEM_SOURCE_REAL_XPC_DICTIONARY_OOL_PORTS_ROUNDTRIP_BIDIRECTIONAL_READONLY_AND_LIFETIME_OK','XPC_SHMEM_SOURCE_BACKING_FDS_RETURN_TO_BASELINE_AFTER_RECONCILIATION_OK'])]
results={}
for label,binary,prior,key,arguments,markers in tests:
 d=json.loads((root/prior).read_text());assert digest(binary)==d[key]
 command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+binary,*arguments];command[3]='100'
 a=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True);text=a.stdout+a.stderr;log='logs/xpc-activation-'+label+'-regression.log';(root/log).write_text(text)
 results[label]=dict(prior_report=prior,prior_report_sha256=digest(prior),binary=binary,binary_sha256=digest(binary),command=command,exit_status=a.returncode,log=log,log_sha256=digest(log),verified=a.returncode==0 and all(marker in text for marker in markers))
 print(label,a.returncode,text[-1600:],flush=True);assert results[label]['verified']
(root/'artifacts/xpc-activation-regressions.json').write_text(json.dumps(dict(checked_at=datetime.now(timezone.utc).isoformat(),source_xpc_activation=p['source_xpc_activation'],source_runtime=p['source_runtime'],results=results,verified=True,full_xcode_build_ready=False),indent=2)+'\n')
