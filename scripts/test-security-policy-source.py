#!/usr/bin/env python3
"""Verify genuine policy objects, complete option dictionaries and old trust integration."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess
root=Path(__file__).resolve().parent.parent
read=lambda p:json.loads((root/p).read_text());digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
build=read('artifacts/security-policy-source.json');probe=read('artifacts/apple-system-info-native-xcode-probe.json')
assert digest(build['library'])==build['library_sha256'] and digest(build['staged_framework'])==build['staged_framework_sha256']
for path,value in build['source_files'].items():assert digest(path)==value
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
guestroot=root/'runtime/rootfs/usr/libexec/darling'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-fblocks','-c',
    str(root/'fixtures/hello/security-external-developer-policy.m'),'-o',str(root/'artifacts/security-external-developer-policy.o')],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(guestroot),
    '-F',str(guestroot/'System/Library/Frameworks'),'-framework','Security','-framework','CoreFoundation','-framework','Foundation',
    '-lobjc','-lSystem',str(root/'artifacts/security-external-developer-policy.o'),'-o',str(root/'artifacts/security-external-developer-policy')],check=True)
environment=os.environ.copy()
for name,item in probe['source_runtime'].items():
    assert digest(item['path'])==item['sha256'];environment[name]=str(root/item['path'])
certificate='vendor/darling/src/external/security/tests/TrustTests/TestData/TestCopyProperties_ios-data/root2048.cer'
guest='/Volumes/SystemRoot/workspace/';logs={};commands={}
markers=['SOURCE_SECURITY_POLICY_NEW_FUNCTION_REAL_BASE_FACTORY_AND_EXISTING_ACCESSOR_OWNERS_OK',
    'SOURCE_SECURITY_POLICY_TRUE_FALSE_ALL_18_15_TYPED_CONSTRAINTS_OIDS_EKU_ROOT_CHAIN_REVOCATION_KEY_SIZES_OK',
    'SOURCE_SECURITY_POLICY_REAL_LEGACY_FACTORY_DIFFERENTIAL_AND_EXACT_EXPIRY_MODE_DELTA_OK',
    'SOURCE_SECURITY_POLICY_GENUINE_CERTIFICATE_AND_TRUST_CONTAINER_ACCEPT_NEW_POLICY_NO_TRUST_EVALUATION_CLAIM_OK',
    'SOURCE_SECURITY_POLICY_OWNED_LIFETIME_MUTATION_ISOLATION_AND_EIGHT_THREADS_128_REAL_OBJECTS_OK']
for mode in ['legacy','native']:
    if mode=='legacy':
        command=['timeout','-k','5','60','bin/darling','shell','/usr/bin/env',
            'DYLD_FRAMEWORK_PATH='+guest+'runtime/security-policy-source/frameworks',
            'DYLD_LIBRARY_PATH='+guest+'runtime/security-policy-source/libraries']
    else:
        command=list(probe['command'][:probe['command'].index('/usr/bin/xcodebuild')])
        for key,prefix in [('DYLD_FRAMEWORK_PATH=',guest+'runtime/security-policy-source/frameworks'),
            ('DYLD_LIBRARY_PATH=',guest+'runtime/security-policy-source/libraries')]:
            index=next(i for i,value in enumerate(command) if value.startswith(key));command[index]=key+prefix+':'+command[index].split('=',1)[1]
    command += [guest+'artifacts/security-external-developer-policy',guest+build['staged_framework'],guest+build['library'],guest+certificate]
    log='logs/security-policy-source-'+mode+'.log'
    with (root/log).open('w') as stream:
        result=subprocess.run(command,cwd=root,env=environment,stdout=stream,stderr=subprocess.STDOUT)
    print(mode,result.returncode,flush=True)
    assert result.returncode==0,(mode,(root/log).read_text()[-6000:])
    assert all(marker+'\n' in (root/log).read_text() for marker in markers)
    logs[log]=digest(log);commands[mode]=command
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),runtime_execution_verified=True,
    selected_runtime=probe['source_runtime'],library=build['library'],library_sha256=build['library_sha256'],
    staged_framework=build['staged_framework'],staged_framework_sha256=build['staged_framework_sha256'],
    source_files=build['source_files'],test_source_sha256=digest('fixtures/hello/security-external-developer-policy.m'),
    test_binary_sha256=digest('artifacts/security-external-developer-policy'),test_driver_sha256=digest('scripts/test-security-policy-source.py'),
    certificate_fixture=certificate,certificate_fixture_sha256=digest(certificate),
    full_typed_option_schema_true_false_verified=True,real_legacy_policy_differential_verified=True,
    actual_policy_factory_and_trust_container_integration_verified=True,
    owned_lifetime_isolation_and_128_concurrent_objects_per_profile_verified=True,
    profiles=['legacy','native'],commands=commands,logs=logs,
    certificate_chain_trust_evaluation_verified=False,trust_backend_modern_check_enforcement_verified=False,
    full_security_source_rebuild=False,full_xcode_build_ready=False,signing_ready=False)
(root/'artifacts/security-policy-source-execution.json').write_text(json.dumps(record,indent=2)+'\n')
print('Source developer-policy construction and genuine Security object/container integration passed in both Foundation profiles')
