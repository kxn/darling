#!/usr/bin/env python3
"""Run real snapshot, TLV, framework and original-Xcode tests with seven components."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess
root=Path(__file__).resolve().parent.parent;digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
selected=json.loads((root/'artifacts/dyld-dlopen-header-source.json').read_text())['selected_runtime']
environment=os.environ.copy()
for variable,item in selected.items():
    assert digest(item['path'])==item['sha256'];environment[variable]=str(root/item['path'])
guest='/Volumes/SystemRoot/workspace/'
entries=[('snapshot',[guest+'artifacts/dyld-process-snapshot',guest+'runtime/dyld-cache-introspection/fixture.dylib'],
    'REAL_DYLD_PROCESS_SNAPSHOT_MACH_IMAGES_UUID_SEGMENTS_CONTENT_LOAD_UNLOAD_FROZEN_STATE_RIGHTS_OK'),
    ('tlv',[guest+'artifacts/metadata-thread-local'],
    'ORIGINAL_METADATA_EXPORTED_TLV_THREE_THREADS_ZERO_INITIALIZATION_DISTINCT_STORAGE_ISOLATION_OK')]
logs={}
for name,tail,marker in entries:
    path=root/('logs/libdyld-source-'+name+'-regression.log')
    command=['timeout','-k','5','45','bin/darling','shell','/usr/bin/env',
        'DYLD_FRAMEWORK_PATH='+guest+'runtime/native-framework-stage',
        'DYLD_LIBRARY_PATH='+guest+'runtime/native-library-stage:'+guest+'runtime/rebuilt-der:/usr/lib/swift',*tail]
    with path.open('w') as stream:subprocess.run(command,cwd=root,env=environment,stdout=stream,stderr=subprocess.STDOUT,check=True)
    assert marker in path.read_text();logs[str(path.relative_to(root))]=digest(path)
for script in ['test-ca-display-native.py','test-quartzcore-native-xcode-version.py']:
    with (root/('logs/libdyld-source-'+script+'.log')).open('w') as stream:
        subprocess.run(['python3','scripts/'+script,'--source-dyld'],cwd=root,stdout=stream,stderr=subprocess.STDOUT,check=True)
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),selected_runtime=selected,
    real_snapshot_images_uuids_segments_load_unload_and_rights_verified=True,
    real_three_thread_native_exported_tlv_storage_isolation_verified=True,
    native_QuartzCore_490_value_cases_verified=True,original_xcode_version_verified=True,
    logs=logs,full_xcode_build_ready=False,signing_ready=False)
(root/'artifacts/libdyld-source-regressions.json').write_text(json.dumps(report,indent=2)+'\n')
print('Seven-component libdyld snapshot/TLV/native-framework/original-version regressions passed')
