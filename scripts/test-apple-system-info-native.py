#!/usr/bin/env python3
"""Run original AppleSystemInfo formatter code and genuine bundle lookups."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,re,subprocess
root=Path(__file__).resolve().parent.parent
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
read=lambda p:json.loads((root/p).read_text())
stage=read('artifacts/apple-system-info-native-stage.json');probe=read('artifacts/mobileasset-source-xcode-probe.json')
assert digest(stage['framework'])==stage['framework_sha256']
for p,value in stage['staged_resources'].items():assert digest(p)==value
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
guestroot=root/'runtime/rootfs/usr/libexec/darling'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-fblocks','-c',
    str(root/'fixtures/hello/apple-system-info-native.m'),'-o',str(root/'artifacts/apple-system-info-native.o')],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(guestroot),
    '-F',str(guestroot/'System/Library/Frameworks'),'-framework','Foundation','-framework','CoreFoundation','-lobjc','-lSystem',
    str(root/'artifacts/apple-system-info-native.o'),'-o',str(root/'artifacts/apple-system-info-native')],check=True)
environment=os.environ.copy()
for name,item in probe['source_runtime'].items():
    assert digest(item['path'])==item['sha256'];environment[name]=str(root/item['path'])
guest='/Volumes/SystemRoot/workspace/'
command=list(probe['command'][:probe['command'].index('/usr/bin/xcodebuild')])
index=next(i for i,v in enumerate(command) if v.startswith('DYLD_FRAMEWORK_PATH='))
command[index]='DYLD_FRAMEWORK_PATH='+guest+'runtime/apple-system-info-native/frameworks:'+command[index].split('=',1)[1]
framework='runtime/apple-system-info-native/frameworks/AppleSystemInfo.framework'
command += [guest+'artifacts/apple-system-info-native',guest+stage['framework'],guest+framework]
log='logs/apple-system-info-native-execute.log'
with (root/log).open('w') as stream:
    result=subprocess.run(command,cwd=root,env=environment,stdout=stream,stderr=subprocess.STDOUT)
text=(root/log).read_text();print(text[-5000:]);assert result.returncode==0,result.returncode
markers=['ORIGINAL_ASI_FUNCTION_OWNER_AND_ACTUAL_RESOURCE_BUNDLE_OK',
    'ORIGINAL_ASI_CPU_DESCRIPTION_25_REAL_COUNT_SPEED_STRING_FORMAT_CASES_OK',
    'ORIGINAL_ASI_CURRENT_TEN_FORMAT_FLAGS_COPY_WRAPPER_AND_AUTORELEASE_LIFETIME_OK']
assert all(marker+'\n' in text for marker in markers)
scalar=re.search(r'NATIVE_COMPOSED_CPU_DESCRIPTION (\d+) (\d+) ',text);assert scalar
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),native_execution_verified=True,
    stage=stage,selected_runtime=probe['source_runtime'],input_probe_sha256=digest('artifacts/mobileasset-source-xcode-probe.json'),
    test_source_sha256=digest('fixtures/hello/apple-system-info-native.m'),test_binary_sha256=digest('artifacts/apple-system-info-native'),
    test_driver_sha256=digest('scripts/test-apple-system-info-native.py'),command=command,exit_status=0,
    native_scalar_format_cases=25,native_current_format_flag_cases=10,
    original_bundle_and_string_lifetime_verified=True,log=log,log_sha256=digest(log),
    complete_frequency_formatting_verified=False,
    observed_native_CPU_package_count=int(scalar[1]),observed_native_frequency_scalar=int(scalar[2]),
    observed_backend_limits=['GHz inputs currently lose the frequency portion through the existing number-formatting backend; only MHz values have exact numeric-output assertions.',
        'Native CPU-kind queries return no platform identity here, and current descriptions use the original Unknown fallback. Full hardware-query unit correctness is not established.'],
    hardware_registry_platform_identity_verified=False,all_29_exports_execution_verified=False,
    full_xcode_build_ready=False,signing_ready=False)
(root/'artifacts/apple-system-info-native-execution.json').write_text(json.dumps(report,indent=2)+'\n')
print('Actual original AppleSystemInfo formatter and resource-backed bundle operations passed')
