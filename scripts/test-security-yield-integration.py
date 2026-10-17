#!/usr/bin/env python3
"""Exercise the existing real snapshot and new policy in the combined profile."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,re,subprocess
root=Path(__file__).resolve().parent.parent
read=lambda p:json.loads((root/p).read_text());digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
probe=read('artifacts/pthread-yield-export-xcode-probe.json');security=read('artifacts/security-policy-source.json')
environment=os.environ.copy()
for name,item in probe['source_runtime'].items():
    assert digest(item['path'])==item['sha256'];environment[name]=str(root/item['path'])
base=list(probe['command'][:probe['command'].index('/usr/bin/xcodebuild')]);guest='/Volumes/SystemRoot/workspace/'
certificate='vendor/darling/src/external/security/tests/TrustTests/TestData/TestCopyProperties_ios-data/root2048.cer'
entries=[('snapshot',[guest+'artifacts/dyld-process-snapshot',guest+'runtime/dyld-cache-introspection/fixture.dylib'],
    'REAL_DYLD_PROCESS_SNAPSHOT_MACH_IMAGES_UUID_SEGMENTS_CONTENT_LOAD_UNLOAD_FROZEN_STATE_RIGHTS_OK'),
    ('policy',[guest+'artifacts/security-external-developer-policy',guest+security['staged_framework'],guest+security['library'],guest+certificate],
    'SOURCE_SECURITY_POLICY_OWNED_LIFETIME_MUTATION_ISOLATION_AND_EIGHT_THREADS_128_REAL_OBJECTS_OK')]
logs={};commands={}
for name,tail,marker in entries:
    log='logs/security-yield-integration-'+name+'.log';command=base+tail
    with (root/log).open('w') as stream:subprocess.run(command,cwd=root,env=environment,stdout=stream,stderr=subprocess.STDOUT,check=True)
    assert re.search(r'(?m)^'+re.escape(marker)+r'(?: \d+)?$',(root/log).read_text())
    logs[log]=digest(log);commands[name]=command
subprocess.run(['python3','scripts/test-quartzcore-native-xcode-version.py','--source-dyld','--source-mobileasset',
    '--native-systeminfo','--source-security-policy','--pthread-yield-export'],cwd=root,check=True)
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),selected_runtime=probe['source_runtime'],
    input_probe_sha256=digest('artifacts/pthread-yield-export-xcode-probe.json'),
    existing_snapshot_images_UUID_segments_load_unload_and_rights_verified=True,
    complete_source_policy_schema_and_128_concurrent_objects_verified=True,
    original_xcode_version_verified=True,commands=commands,logs=logs,
    full_xcode_build_ready=False,signing_ready=False)
(root/'artifacts/security-yield-integration.json').write_text(json.dumps(record,indent=2)+'\n')
print('Combined source policy / named pthread export profile preserves actual snapshots, policy objects and original Xcode version')
