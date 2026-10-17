#!/usr/bin/env python3
"""Record real local volume-reference diagnosis and executed source directory repair."""
from pathlib import Path
from datetime import datetime,timezone
import ast,fcntl,hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
read=lambda n:json.loads((root/n).read_text());digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest();evidence={}
def add(n,sha=None):
    actual=digest(n)
    if sha is not None:assert actual==sha,n
    evidence[n]=actual
p=runpy.run_path(str(root/'scripts/coreservices-directories-profile.py'))['profile']()
control=runpy.run_path(str(root/'scripts/coreservices-directories-profile.py'))['profile'](baseline=True)
build=p['source_coreservices_directories'];baseline=control['source_coreservices_directories']
for d in [build,baseline]:
    assert d['complete_source_files']==3 and d['exports_preserved']==8
    add(d['library'],d['library_sha256']);add(d['variant_root']+'/usr/lib/system/libsystem_coreservices.dylib',d['library_sha256'])
    for item in d['sources']:
        add(item['source'],item['sha256']);add(item['object'],item['object_sha256'])
    for item in d['source_runtime'].values():add(item['path'],item['sha256'])
for path,sha in build['source_headers'].items():add(path,sha)
for n in ['artifacts/coreservices-directories-source-v2-build.json','artifacts/coreservices-directories-baseline-build.json']:add(n)
for variant,d in [('source',build),('baseline',baseline)]:
    n='artifacts/coreservices-directories-'+variant+'-test.json';test=read(n);add(n);assert test['coreservices']==d
    for key in ['source','binary','log']:add(test[key],test[key+'_sha256'])
    text=(root/test['log']).read_text()
    if variant=='source':assert test['exit_status']==0 and test['runtime_execution_verified'] and 'DIRECTORY_HELPER_FUNCTIONAL_OK checks=156' in text
    else:assert test['exit_status']==1 and not test['runtime_execution_verified'] and 'expr=stat(path,&st)==0 errno=2' in text
analysis=read('artifacts/fileidtree-local-volume-reference-analysis.json');add('artifacts/fileidtree-local-volume-reference-analysis.json')
for key in ['image','disassembly']:add(analysis[key],analysis[key+'_sha256'])
rootprobe=read('artifacts/fileidtree-root-trace.json');add('artifacts/fileidtree-root-trace.json')
assert rootprobe['exit_status']==0 and rootprobe['probe_returned'] and rootprobe['debugger_exit_status']==0
for key in ['log','source','binary','trace','maps']:add(rootprobe[key],rootprobe[key+'_sha256'])
trace=(root/rootprobe['trace']).read_text()
for token in ['once_block','server_callbacks=1','root_statfs_return rax=0x0','root_mount_return rax=0x','device_0x4c=00000000','caps_0x98=20100000','path_0xb0=0f000000']:assert token in trace,token
assert 'network_disable_return' not in trace # skipped before reaching the network filter
service_name='artifacts/fileidtree-service-sandbox-resources-source-dirs-dirhelper-trace-original-compiler.json';service=read(service_name);add(service_name)
assert service['source_coreservices_directories']==build and service['debugger_exit_status']==0
assert service['exit_status'] in [-9,124]
for key in ['log','script','trace','trace_script','maps']:add(service[key],service[key+'_sha256'])
for path,sha in service['service_logs'].items():add(path,sha)
for job in service['jobs']:
    assert not job['binary_modified'] and job['source_sha256']==job['selected_sha256']
    for key in ['source','selected','original_plist']:add(job[key],job[key+'_sha256'])
    add(job['path'],job['sha256'])
text=(root/service['trace']).read_text()
for token in ['CORESERVICES_TRACE server_main','user_temp_confstr_return','user_cache_confstr_return','cache_realpath_return  rax=0x','sandbox_init_return  rax=0xffffffff','native_sandbox_params_return  rax=0x','native_sandbox_compile_return  rax=0x','native_sandbox_apply_return  rax=0xffffffff','sandbox_profile_failure Operation not supported','exited with code 01']:assert token in text,token
assert 'bootstrap_checkin_return' not in text
compiler_profile=runpy.run_path(str(root/'scripts/sandbox-compiler-resources-profile.py'))['profile']()
assert service['native_sandbox_compiler']==compiler_profile['native_sandbox_compiler']
assert service['original_sandbox_resources']==compiler_profile['original_sandbox_resources']
for target,item in compiler_profile['native_sandbox_compiler'].items():
    for key in ['original','library','reconstruction']:add(item[key],item[key+'_sha256'])
    d=read(item['reconstruction']);assert not d['backend_call_overrides']
    assert item['exports']==(36 if target=='sandbox-compiler-native' else 13)
resources=compiler_profile['original_sandbox_resources'];add('artifacts/sandbox-compiler-resources-stage.json')
assert len(resources['resource_files'])==533 and not resources['resources_modified']
for path,item in resources['resource_files'].items():add(path,item['sha256']);add(item['source'],item['sha256'])
for item in resources['source_runtime'].values():add(item['path'],item['sha256'])
for control_case in [False,True]:
    n='artifacts/sandbox-compiler-'+('baseline' if control_case else 'native')+'-probe.json';test=read(n);add(n)
    for key in ['source','binary','log']:add(test[key],test[key+'_sha256'])
    text=(root/test['log']).read_text()
    if control_case:assert test['exit_status']==2 and 'STUB: sandbox_create_params called' in text and 'ptr=0x0 errno=33' in text
    else:
        assert test['exit_status']==0 and test['probe_returned'] and not test['policy_applied']
        for i in [0,1]:assert re.search('RESULT index='+str(i)+r' ptr=0x[1-9a-f][0-9a-f]* errno=0 error=nil',text)
        for i in [2,3]:assert 'RESULT index='+str(i)+' ptr=0x0' in text
        assert 'unbound variable: not-a-real-sandbox-operation' in text and "syntax error: expecting ')'" in text
for n in ['artifacts/sandbox-compiler-loader-history/manifest.json','artifacts/sandbox-compiler-eager-history/manifest.json']:
    add(n)
    for item in read(n).values():add(item['archived'],item['sha256'])
for n in ['scripts/sandbox-compiler-native-profile.py','scripts/stage-sandbox-compiler-resources.py','scripts/sandbox-compiler-resources-profile.py','scripts/probe-sandbox-compiler-native.py']:
    ast.parse((root/n).read_text());add(n)
for n in ['fixtures/hello/sandbox-compiler-native.c','vendor/darling/src/libsandbox/src/sandbox.c','runtime/coreservices-directories-source-v2/darling-root/usr/lib/libsandbox.1.dylib','vendor/darlingserver/src/call.cpp','vendor/darling/src/external/xnu/darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/impl/misc/mac_syscall.c']:add(n)
for n in ['artifacts/dirhelper-source-history/manifest.json','artifacts/dirhelper-first-source-attempt/manifest.json','artifacts/native-crypto-before-dirhelper-history/manifest.json']:
    d=read(n);add(n)
    for item in d.values():add(item['archived'],item['sha256'])
for n in ['scripts/build-coreservices-directories-source.py','scripts/coreservices-directories-profile.py','scripts/test-coreservices-directories.py','scripts/probe-fileidtree-root.py','scripts/probe-fileidtree-service.py','scripts/record-fileidtree-directory-progress.py']:
    ast.parse((root/n).read_text());add(n)
for n in ['fixtures/hello/coreservices-directories.c','fixtures/hello/fileidtree-root.m','artifacts/darling-coreservices-directory-source.patch','runtime/recovery/macOS Base System/System/Library/Sandbox/Profiles/com.apple.coreservicesd.sb','vendor/darling/src/sandbox/sandbox.c']:add(n)
subprocess.run(['git','-C',str(root/'vendor/darling'),'apply','--reverse','--check',str(root/'artifacts/darling-coreservices-directory-source.patch')],check=True)
with (root/'runtime/session.lock').open('a') as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),goal_status='active',complete=False,full_xcode_build_ready=False,signing_ready=False,default_entry_promoted=False,local_root_device_exists=True,local_root_legacy_volume_reference=0,earlier_empty_device_table_hypothesis_corrected=True,complete_source_files=3,exports_preserved=8,directory_checks=156,old_source_fails_missing_cache_directory=True,source_coreservices_directories=build,original_coreservicesd_binary_modified=False,original_coreservicesd_directory_initialization_succeeded=True,original_coreservicesd_reached_bootstrap=False,original_coreservicesd_exit_status=1,sandbox_error='Operation not supported',stock_sandbox_compiler_param_creation_returns_NULL_without_setting_errno=True,prior_ENOENT_message_was_not_proof_of_missing_profile=True,original_sandbox_compiler_exports=36,original_match_engine_exports=13,sandbox_compiler_valid_programs=2,sandbox_compiler_invalid_programs_rejected=2,original_profile_resource_files=533,original_coreservicesd_profile_compiled=True,native_sandbox_apply_return=-1,original_compiler_selected_eager_loading_verified=False,original_compiler_eager_loading_gap='__dyld_dlsym_blocked in LoggingSupport; actual original caller uses RTLD_LAZY',native_sandbox_compiler=compiler_profile['native_sandbox_compiler'],original_sandbox_resources=resources,sandbox_profile_enforcement_implemented=False,native_volume_enumeration_fixed=False,original_shared_FileIDTree_service_functional=False,original_FileCoordination_service_functional=False,new_full_Xcode_build_attempted=False,path_layout_scope='Preserves Darling HOME/TMPDIR directory layout; not a complete implementation of Apple UUID user-directory allocation, profile enforcement or shared CoreServices services.',evidence=evidence,next_work=['Implement genuine Sandbox profile application/enforcement for the unchanged original CoreServices server. Original parameters and named SBPL compilation now succeed; actual Sandbox MAC operation 0 returns ENOTSUP before bootstrap check-in. Decode/validate real compiled policy and enforce its decisions rather than reporting fabricated success.','Start the real CoreServices/FileIDTree service and inspect legacy volume-reference assignment and real shared-volume enumeration; local fallback root insertion succeeds but its unassigned reference is filtered.','Restore genuine FileCoordination and retry unchanged original Xcode project compilation; continue through Unity/CocoaPods, archive, signing and export.'])
(root/'artifacts/fileidtree-directory-progress.json').write_text(json.dumps(record,indent=2)+'\n');print('Recorded',len(evidence),'directory/FileIDTree evidence hashes')
