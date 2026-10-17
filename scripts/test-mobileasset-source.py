#!/usr/bin/env python3
"""Verify actual Pallas wire transport in legacy and original Foundation runtimes."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess
root=Path(__file__).resolve().parent.parent
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
read=lambda p:json.loads((root/p).read_text())
build=read('artifacts/mobileasset-source.json');probe=read('artifacts/quartzcore-native-source-dyld-probe.json')
assert digest(build['framework'])==build['framework_sha256']
for path,value in build['source_files'].items():assert digest(path)==value
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
guestroot=root/'runtime/rootfs/usr/libexec/darling'
fixtures=['mobileasset-pallas','mobileasset-pallas-operations']
for name in fixtures:
    subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-fblocks',
        '-c',str(root/('fixtures/hello/'+name+'.m')),'-o',str(root/('artifacts/'+name+'.o'))],check=True)
    subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(guestroot),
        '-F',str(guestroot/'System/Library/Frameworks'),'-framework','Foundation','-framework','CoreFoundation',
        '-lobjc','-lSystem',str(root/('artifacts/'+name+'.o')),'-o',str(root/('artifacts/'+name))],check=True)
environment=os.environ.copy()
for name,item in probe['source_runtime'].items():
    assert digest(item['path'])==item['sha256'];environment[name]=str(root/item['path'])
guest='/Volumes/SystemRoot/workspace/';commands={};logs={}
markers={'mobileasset-pallas':['MOBILEASSET_PALLAS_API_OWNED_BY_ACTUAL_SOURCE_FRAMEWORK_OK',
    'MOBILEASSET_PALLAS_REAL_ABSENT_SERVICE_FAILURE_AND_BOOLEAN_OUTPUT_ABI_OK',
    'MOBILEASSET_PALLAS_REAL_FORKED_XPC_NATIVE_ENVELOPE_TRUE_FALSE_WIDE_ERRORS_NULL_NONSTRING_AND_TYPED_REPLIES_OK',
    'MOBILEASSET_PALLAS_REAL_EIGHT_THREADS_64_INDEPENDENT_XPC_REQUEST_REPLY_CYCLES_OK'],
    'mobileasset-pallas-operations':['PALLAS_ALL_DVT_OPERATIONS_AND_DEFAULT_ALIASES_OWNED_BY_SOURCE_FRAMEWORK_OK',
        'PALLAS_ABSENT_SERVICE_STRING_NIL_STATUS_ERRORS_AND_INVALID_NSURL_PRECEDENCE_OK',
        'PALLAS_REAL_XPC_32_SEQUENTIAL_SETTERS_STRING_GETTER_UTF8_POOL_LIFETIME_URL_CLEAR_DEFAULTS_AND_WIDE_ERRORS_OK',
        'PALLAS_REAL_XPC_EIGHT_THREADS_64_MIXED_FIVE_OPERATION_REQUEST_REPLY_CYCLES_OK',
        'PALLAS_REAL_XPC_PEER_TEARDOWN_ONE_RETRY_SUCCESS_AND_TWO_ATTEMPT_LIMIT_OK']}
for mode in ['legacy','native']:
    if mode=='legacy':command=['timeout','-k','5','90','bin/darling','shell']
    else:
        command=list(probe['command'][:probe['command'].index('/usr/bin/xcodebuild')])
        index=next(i for i,v in enumerate(command) if v.startswith('DYLD_FRAMEWORK_PATH='))
        command[index]='DYLD_FRAMEWORK_PATH='+guest+'runtime/mobileasset-source/frameworks:'+command[index].split('=',1)[1]
    for name in fixtures:
        selected_command=command+[guest+'artifacts/'+name,guest+build['framework']]
        log='logs/'+name+'-'+mode+'.log'
        with (root/log).open('w') as stream:
            result=subprocess.run(selected_command,cwd=root,env=environment,stdout=stream,stderr=subprocess.STDOUT)
        print(mode,name,result.returncode,flush=True)
        assert result.returncode==0,(mode,name,(root/log).read_text()[-4000:])
        assert all(marker+'\n' in (root/log).read_text() for marker in markers[name])
        commands[mode+'/'+name]=selected_command;logs[log]=digest(log)
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),runtime_execution_verified=True,
    framework=build['framework'],framework_sha256=build['framework_sha256'],
    selected_runtime=probe['source_runtime'],source_files=build['source_files'],
    test_source_sha256=digest('fixtures/hello/mobileasset-pallas.m'),test_binary_sha256=digest('artifacts/mobileasset-pallas'),
    test_driver_sha256=digest('scripts/test-mobileasset-source.py'),
    tested_files={p:digest(p) for name in fixtures for p in ['fixtures/hello/'+name+'.m','artifacts/'+name]},
    native_analysis_sha256=digest('artifacts/mobileasset-pallas-native-analysis.json'),
    commands=commands,logs=logs,actual_named_xpc_transport_verified=True,
    absent_service_is_failure_verified=True,boolean_and_signed_64bit_status_independent_verified=True,
    legacy_and_original_foundation_verified=True,requests_per_mode=174,concurrent_threads_per_mode=8,
    all_five_DVT_operations_and_legacy_aliases_verified=True,string_return_utf8_autorelease_lifetime_verified=True,
    url_class_validation_and_nil_clear_verified=True,concurrent_requests_per_mode=128,
    real_Apple_daemon_interoperation_verified=False,MobileAsset_download_daemon_implemented=False,
    connection_interruption_retry_execution_verified=True,retry_limit_execution_verified=True,
    full_xcode_build_ready=False,signing_ready=False)
(root/'artifacts/mobileasset-pallas-source.json').write_text(json.dumps(report,indent=2)+'\n')
build.update(runtime_execution_verified=True,execution_report='artifacts/mobileasset-pallas-source.json')
(root/'artifacts/mobileasset-source.json').write_text(json.dumps(build,indent=2)+'\n')
print('Actual MobileAsset Pallas client transport passed in both Foundation runtimes')
