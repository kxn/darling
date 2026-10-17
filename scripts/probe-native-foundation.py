#!/usr/bin/env python3
"""Record the separate native Foundation load attempt and exact diagnostic."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
import json
import subprocess
import argparse

project=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--trace-startup',action='store_true')
args=parser.parse_args()
config=json.loads((project/'config/foundation-native-experiment.json').read_text())
pins=json.loads((project/'config/cache-image-pins.json').read_text())
images={}
for entry in config['targets']:
    target=entry['target'];name=Path(pins[target]['path']).name
    source=project/('runtime/rebuilt-'+target)/name
    reconstruction=json.loads((source.parent/'reconstruction.json').read_text())
    path=project/config['library_stage']/entry.get('stage_name',name) if name.endswith('.dylib') else \
        project/config['framework_stage']/(name+'.framework')/name
    actual=hashlib.sha256(path.read_bytes()).hexdigest()
    if actual!=reconstruction['staged_image_sha256']:
        raise ValueError('Staged image differs from reconstruction: '+target)
    images[target]={'sha256':actual,'execution_verified':False}
inventory=project/'artifacts/foundation-native-dependency-inventory.json'
command=['python3','scripts/inventory-runtime-dependencies.py','--framework-stage',
    config['framework_stage'],'--library-stage',config['library_stage'],
    '--native-stage','--library-path','/usr/lib/swift','--seed',pins['foundation-native']['path'],
    '--output',str(inventory)]
with (project/'logs/foundation-native-dependency-inventory.log').open('w') as log:
    inventory_status=subprocess.run(command,cwd=project,stdout=log,stderr=subprocess.STDOUT).returncode
with (project/'logs/foundation-native-symbol-audit.log').open('w') as log:
    subprocess.run(['python3','scripts/audit-runtime-symbols.py','--inventory',str(inventory),
        '--output',str(project/'artifacts/foundation-native-symbol-audit.json')],
        cwd=project,stdout=log,stderr=subprocess.STDOUT,check=True)
guest='/Volumes/SystemRoot/workspace/'
sdk=project/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
root=project/'runtime/rootfs/usr/libexec/darling'
obj=project/'artifacts/native-foundation-load.o';probe=project/'artifacts/native-foundation-load'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),
    '-c',str(project/'fixtures/hello/native-foundation-load.c'),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11',
    '-syslibroot',str(root),'-L',str(root/'usr/lib'),'-lSystem',str(obj),'-o',str(probe)],check=True)
command=['timeout','-k','5','30','bin/darling','shell','/usr/bin/env',
    'DYLD_FRAMEWORK_PATH='+guest+config['framework_stage']+':'+guest+'runtime/native-framework-stage',
    'DYLD_LIBRARY_PATH='+guest+config['library_stage']+':'+guest+'runtime/native-library-stage:'+guest+'runtime/rebuilt-der:/usr/lib/swift',
    *(['DYLD_PRINT_LIBRARIES=1','DYLD_PRINT_INITIALIZERS=1'] if args.trace_startup else []),
    guest+'artifacts/native-foundation-load',guest+config['framework_stage']+'/Foundation.framework/Foundation']
log_path=project/'logs/foundation-native-load.log'
with log_path.open('w') as log:
    status=subprocess.run(command,cwd=project,stdout=log,stderr=subprocess.STDOUT).returncode
diagnostic=log_path.read_text()
main_entered='NATIVE_FOUNDATION_PROBE_MAIN_ENTERED' in diagnostic
verified=status==0 and 'NATIVE_FOUNDATION_DLOPEN_COMPLETED' in diagnostic
conflicts=[line for line in diagnostic.splitlines() if 'is implemented in both' in line]
report={'checked_at':datetime.now(timezone.utc).isoformat(),'installed':False,
    'full_compatibility':False,'images':images,'inventory_exit_status':inventory_status,
    'load_exit_status':status,'load_verified':verified,'api_execution_verified':False,
    'main_entered':main_entered,'failure_phase':None if verified else ('dlopen' if main_entered else 'process_startup'),
    'duplicate_class_conflicts':conflicts,
    'diagnostic':diagnostic,'command':command,
    'scope':config['scope']}
(project/'artifacts/foundation-native-experiment.json').write_text(json.dumps(report,indent=2)+'\n')
print('Native Foundation load verified:',verified,'status:',status)
raise SystemExit(0 if verified else 1)
