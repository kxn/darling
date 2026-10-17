#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/s2c-lifecycle-runtime-profile.py'));p=m['profile']();digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
tests=[('memory','artifacts/memory-entry-source','artifacts/darlingserver-memory-entry.json','test_binary_sha256',r'MEMORY_ENTRY_SOURCE_REAL_INTERPROCESS_MACH_CAPABILITY_BIDIRECTIONAL_SHARING_AFTER_PORT_RELEASE_OK'),
 ('power','runtime/iokitd-matching-tests/power','artifacts/iokitd-matching-power-regression.json','binary_sha256',r'IOKIT_POWER_SERVICE_OK checks=(\d+) cycles=128 physical_ool_cases=7'),
 ('matching','runtime/iokitd-matching-tests/test','artifacts/iokitd-matching-test.json','binary_sha256',r'IOKIT_MATCHING_NATIVE_CALLBACKS_OK checks=(\d+) callbacks=11 cycles=128')]
results={}
for name,binary,prior,key,marker in tests:
 old=json.loads((root/prior).read_text());assert digest(binary)==old[key]
 command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+binary];command[3]='100'
 a=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True);text=a.stdout+a.stderr;log='logs/s2c-runtime-'+name+'-regression.log';(root/log).write_text(text)
 match=re.search(marker,text);d=dict(prior_report=prior,prior_report_sha256=digest(prior),binary=binary,binary_sha256=digest(binary),command=command,exit_status=a.returncode,log=log,log_sha256=digest(log),verified=a.returncode==0 and match is not None)
 if name=='memory':
  for required in ['MEMORY_ENTRY_SOURCE_ALIAS_SUBRANGE_PARTIAL_UNMAP_READONLY_NO_WRITE_ESCALATION_32_CYCLES_FD_CLEANUP_OK','MEMORY_ENTRY_SOURCE_ADDRESS_REUSE_INVALID_CAPABILITIES_FLAGS_BOUNDS_AND_32_CONCURRENT_MAPS_OK']:assert required in text
 else:d['checks']=int(match[1]) if match else 0
 results[name]=d;print(name,a.returncode,text[-1500:],flush=True);assert d['verified']
(root/'artifacts/s2c-runtime-regressions.json').write_text(json.dumps(dict(checked_at=datetime.now(timezone.utc).isoformat(),source_runtime=p['source_runtime'],source_s2c_lifecycle=p['source_s2c_lifecycle'],results=results,verified=True,full_xcode_build_ready=False),indent=2)+'\n')
