#!/usr/bin/env python3
"""Exercise original QuartzCore mode-value APIs, without creating a display."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-dyld',action='store_true');args=parser.parse_args()
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
probe_path='artifacts/quartzcore-native-source-dyld-probe.json' if args.source_dyld else 'artifacts/quartzcore-native-probe.json'
probe=json.loads((root/probe_path).read_text())
image=probe['native_quartzcore'];assert digest(image['staged_framework'])==image['staged_framework_sha256']
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
guest_root=root/'runtime/rootfs/usr/libexec/darling'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-fblocks','-O2',
    '-c',str(root/'fixtures/hello/ca-display-native-values.m'),'-o',str(root/'artifacts/ca-display-native-values.o')],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(guest_root),
    '-F',str(guest_root/'System/Library/Frameworks'),'-framework','Foundation','-framework','CoreFoundation','-lobjc','-lSystem',
    str(root/'artifacts/ca-display-native-values.o'),'-o',str(root/'artifacts/ca-display-native-values')],check=True)
environment=os.environ.copy()
for variable,item in probe['source_runtime'].items():
    assert digest(item['path'])==item['sha256'];environment[variable]=str(root/item['path'])
command=list(probe['command']);index=command.index('/usr/bin/xcodebuild')
command[index:]=['/Volumes/SystemRoot/workspace/artifacts/ca-display-native-values',
    '/Volumes/SystemRoot/workspace/'+image['staged_framework']]
log=root/('logs/ca-display-native-values-source-dyld.log' if args.source_dyld else 'logs/ca-display-native-values.log')
with log.open('w') as stream:
    result=subprocess.run(command,cwd=root,env=environment,stdout=stream,stderr=subprocess.STDOUT)
success=result.returncode==0 and 'CA_DISPLAY_ORIGINAL_NATIVE_FACTORY_DIMENSIONS_RATES_VRR_PACKING_EQUALITY_AND_DATA_COPY_OK 490\n' in log.read_text()
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),installed=False,full_compatibility=False,
    selected_native_mode_value_api_execution_verified=success,exit_status=result.returncode,
    native_framework=image,source_runtime=probe['source_runtime'],command=command,
    test_source_sha256=digest('fixtures/hello/ca-display-native-values.m'),
    test_binary_sha256=digest('artifacts/ca-display-native-values'),
    native_metadata_analysis_sha256=digest('artifacts/ca-display-native-analysis.json'),
    native_DVT_callers_sha256=digest('artifacts/ca-display-dvt-callers.json'),
    input_probe_sha256=digest(probe_path),
    log=str(log.relative_to(root)),log_sha256=digest(log),diagnostic=log.read_text(),
    display_enumeration_verified=False,renderer_or_GPU_implemented=False,full_xcode_build_ready=False,signing_ready=False)
(root/('artifacts/ca-display-native-values-source-dyld.json' if args.source_dyld else 'artifacts/ca-display-native-values.json')).write_text(json.dumps(report,indent=2)+'\n')
print('Actual original CADisplayMode value API test:',result.returncode)
raise SystemExit(0 if success else 1)
