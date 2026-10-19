#!/usr/bin/env python3
"""Record verified original crypto and the real remaining FileIDTree failure."""
from pathlib import Path
from datetime import datetime,timezone
import ast,fcntl,hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
read=lambda n:json.loads((root/n).read_text())
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
evidence={}
resolve_evidence=runpy.run_path(str(root/'scripts/resolve-evidence-history.py'))['resolve']
def add(n,sha=None):
    if sha is not None:
        n=resolve_evidence(str(n),sha)
    actual=digest(n)
    if sha is not None:assert actual==sha,n
    evidence[str(n)]=actual
def walk(value):
    if isinstance(value,list):
        for item in value:walk(item)
    elif isinstance(value,dict):
        for key,item in value.items():
            if isinstance(item,str) and isinstance(value.get(key+'_sha256'),str) and (root/item).is_file():add(item,value[key+'_sha256'])
            if key=='sha256':
                for pkey in ['source','path','file']:
                    if pkey+'_sha256' not in value and isinstance(value.get(pkey),str) and (root/value[pkey]).is_file():add(value[pkey],item)
            if isinstance(item,str) and re.fullmatch('[a-f0-9]{64}',item) and (root/key).is_file():add(key,item)
            if isinstance(item,(dict,list)):walk(item)
def report(n,fields=None):
    d=read(n);add(n);walk(d if fields is None else {k:d[k] for k in fields});return d

p=runpy.run_path(str(root/'scripts/commoncrypto-original-profile.py'))['profile']()
runtime=p['source_runtime']
for item in runtime.values():add(item['path'],item['sha256'])
source=report('artifacts/corecrypto-hkdf-source-build.json');assert source['complete_source_files']==56 and source['original_exports_preserved']==402
assert source['BoringSSL']['source_revision']=='95ba0316a9b733e92bb6b071255ff46263bbe7dc'
native_case_counts={};source_case_counts={}
for name,count,key in [('hkdf',210,'independent_HMAC_HKDF_cases'),('ctr',81,'independent_OpenSSL_cases'),('sha3',236,'independent_SHA3_HMAC_HKDF_cases'),('25519',113,'independent_cryptography_cases')]:
    for native in [False,True]:
        n='artifacts/corecrypto-'+name+'-'+('native-' if native else '')+'test.json';d=report(n)
        assert d['runtime_execution_verified'] and d['exit_status']==0 and d[key]==count
        assert d['corecrypto']==(p['native_original_corecrypto'] if native else source)
        assert d['invalid_null_pointer_preconditions_exercised']==(not native)
        (native_case_counts if native else source_case_counts)[name]=count

selected={}
for key in ['native_applearchive','native_argument_parser','native_original_cryptokit','native_original_corecrypto','native_original_commoncrypto','native_crypto_token_kit','corecrypto_malloc','source_token_parameters','source_security_cryptokit_constants','source_local_authentication']:
    walk(p[key])
targets={'corecrypto-original-native-v2':1088,'commoncrypto-original-native':245,'cryptokit-native-original':1823,'cryptokit-cbridging-native-original':29,'crypto-token-kit-native-original':207,'apple-archive-crypto-native':232,'swift-apple-archive-crypto-native':909,'swift-compression-archive-native':70,'argument-parser-internal-native':707}
for target,count in targets.items():
    d=report('runtime/rebuilt-'+target+'/reconstruction.json');assert d['exports']==count and not d['backend_call_overrides']
    assert d['redirected_imports']==(['_malloc_type_malloc'] if target in ['corecrypto-original-native-v2','commoncrypto-original-native'] else [])
    selected[target]=dict(exports=count,reconstruction_sha256=digest('runtime/rebuilt-'+target+'/reconstruction.json'),typed_allocator_redirect=bool(d['redirected_imports']))
loaded=report('artifacts/local-authentication-error-load.json');assert loaded['all_selected_images_load'] and len(loaded['checks'])==4
assert all(c['exit_status']==0 and c['native_dlopen_verified'] for c in loaded['checks'])
sdk=report('artifacts/cryptokit-original-test.json');assert sdk['runtime_execution_verified'] and sdk['independent_crypto_results']==11 and sdk['original_Apple_SDK_interface_used']
assert sdk['corecrypto']==p['native_original_corecrypto'] and sdk['cryptokit']==p['native_original_cryptokit']
assert all(c['exit_status']==0 for c in sdk['checks'])
constants=report('artifacts/native-crypto-constants-test.json');assert constants['runtime_execution_verified'] and len(constants['constants'])==17
archive=report('artifacts/applearchive-native-original-test.json',['checks','sources','binaries','native_applearchive','native_original_corecrypto','native_original_commoncrypto'])
assert archive['runtime_execution_verified'] and archive['native_original_commoncrypto']==p['native_original_commoncrypto']
text=(root/archive['checks'][-1]['log']).read_text()
for marker in ['NATIVE_ARCHIVE_COMPRESSION_OK '+n+' 65537' for n in ['none','zlib','lz4','lzfse']]+['NATIVE_ARCHIVE_ENCRYPTION_ROUNDTRIP_OK 65537','NATIVE_ARCHIVE_WRONG_KEY_REJECTED','NATIVE_ARCHIVE_CORRUPTION_REJECTED']:
    assert marker in text,marker
regression=report('artifacts/native-crypto-regression.json',['checks']);assert len(regression['checks'])==6 and all(c['exit_status']==0 for c in regression['checks'])
assert regression['native_original_commoncrypto']==p['native_original_commoncrypto']
assert 'cases=852' in (root/regression['checks'][-1]['log']).read_text() and 'checks=13385084' in (root/regression['checks'][-1]['log']).read_text()

probes={}
for mode,pattern in [('version','xcode-service-runtime-nativecrypto-parser*version.json'),('showsdks','xcode-service-runtime-nativecrypto-parser*showsdks.json'),('build','xcode-service-runtime-coordination-nativecrypto-parser*build.json')]:
    names=list((root/'artifacts').glob(pattern));assert len(names)==1;name=str(names[0].relative_to(root))
    d=report(name,['jobs','service_logs','original_preference_service','original_filecoordination_service'])
    for key in ['log','script']:add(d[key],d[key+'_sha256'])
    assert d['UTI_preflight_verified'] and d['xcode_process_started'] and d['native_original_commoncrypto']==p['native_original_commoncrypto']
    log=(root/d['log']).read_text()
    assert 'Symbol not found: _$s9CryptoKit' not in log and 'Symbol not found: _$s12AppleArchive' not in log
    if mode!='build':assert d['exit_status']==0 and 'SERVICE_RUNTIME_XCODE_STATUS 0' in log
    else:
        assert d['exit_status']==-9 and 'SERVICE_RUNTIME_XCODE_STATUS 132' in log
        service=d['original_filecoordination_service'];assert not service['binary_modified']
        assert '"Program" = "/Volumes/SystemRoot/workspace/'+service['selected']+'";' in log
        assert 'CompileC ' not in log and 'SwiftCompile ' not in log
        daemon=next(c for c in d['jobs'] if c['name']=='filecoordination');daemonlog=daemon['job']['StandardOutPath'].removeprefix('/Volumes/SystemRoot/workspace/')
        assert 'Error occurred while attempting to enumerate volumes:' in (root/daemonlog).read_text()
    probes[mode]=dict(report=name,report_sha256=digest(name),wrapper_exit_status=d['exit_status'],original_xcode_returned=d['xcode_process_returned'])

volumes=report('artifacts/native-volumes-probe.json');assert volumes['probe_returned'] and volumes['exit_status']==0
vtext=(root/volumes['log']).read_text()
for marker in ['NATIVE_VOLUMES_GETMNTINFO count=10 errno=0','NATIVE_VOLUMES_GETMNTINFO_R count=10 errno=0','FILEIDTREE_MOUNT_POINTS status=0 count=0','CF_MOUNT_ENUMERATOR_NEXT result=3 url=0x0 error_domain=NSCocoaErrorDomain error_code=256','NATIVE_VOLUMES_FOUNDATION count=0 nil=1']:
    assert marker in vtext,marker
assert 'VOLUME_METHOD_OWNER' in vtext and 'foundation-native-framework-stage/Foundation.framework' in vtext
directory_phase=report('artifacts/fileidtree-directory-progress.json');assert directory_phase['directory_checks']==156 and directory_phase['original_coreservicesd_profile_compiled'] and not directory_phase['sandbox_profile_enforcement_implemented']
policy_phase=report('artifacts/native-sandbox-policy-progress.json')
assert policy_phase['semantic_cases']==6034 and policy_phase['malformed_and_mutation_cases']==6488
assert policy_phase['runtime_upload_checks']==216 and policy_phase['runtime_uploads_decoded']==29
assert policy_phase['real_coreservices_profile_decoded'] and not policy_phase['profile_application_implemented']
launchd_phase=report('artifacts/launchd-sandbox-progress.json')
assert launchd_phase['enabled_audit_query_sites']==11 and launchd_phase['real_Mach_checks']==144
assert launchd_phase['controlled_negative_route_checks']==104 and launchd_phase['controlled_query_events']==34
assert launchd_phase['original_xcode_SDK_listing_with_services_passed'] and not launchd_phase['profile_application_implemented']
fs_phase=report('artifacts/sandbox-fs-progress.json')
assert fs_phase['real_filesystem_checks']==338 and fs_phase['controlled_filesystem_checks']==251
assert fs_phase['controlled_query_events']==60 and fs_phase['regression_checks']==6
assert fs_phase['pinned_parent_path_replacement_checked'] and not fs_phase['profile_application_implemented']
current_phase=report('artifacts/unrestricted-sandbox-fsevents-progress.json')
disk_phase=report('artifacts/diskarbitration-log-compose-progress.json')
power_phase=report('artifacts/iokitd-power-progress.json')
matching_phase=report('artifacts/iokitd-matching-progress.json')
mount_phase=report('artifacts/mount-flags-progress.json')
s2c_phase=report('artifacts/s2c-lifecycle-progress.json')
xpc_materialize_phase=report('artifacts/xpc-activation-materialize-progress.json')
mobileasset_query_phase=report('artifacts/mobileasset-query-progress.json')
icu_signal_phase=report('artifacts/icu-signal-progress.json')
fsevents_history_phase=report('artifacts/fsevents-history-progress.json')
global_fsevents_phase=report('artifacts/global-fsevents-progress.json')
assert global_fsevents_phase['original_macos_test_project_build_succeeded']
assert global_fsevents_phase['original_full_SDK_stat_cache_generation_reuse_and_Clang_consumer_verified']
assert fsevents_history_phase['main_queue_CFRunLoop_history_consumer_terminates']
assert not fsevents_history_phase['global_event_ids_implemented']
assert icu_signal_phase['native_ICU_checks']==157 and icu_signal_phase['original_build_tasks_executed']
assert not icu_signal_phase['actual_project_compilation_started']
assert mobileasset_query_phase['native_query_checks']==1823 and mobileasset_query_phase['original_Xcode_MobileAsset_Swift_continuation_leak_resolved']
assert not mobileasset_query_phase['actual_project_compilation_started']
assert xpc_materialize_phase['original_filecoordinationd_granted_actual_Xcode_claims']>=2
assert not xpc_materialize_phase['actual_project_compilation_started']
assert s2c_phase['original_filecoordinationd_received_actual_Xcode_claim']
assert not s2c_phase['public_API_calls_used_in_Xcode_launch']
assert mount_phase['original_root_and_SystemRoot_descriptions_after_real_mount_verified']
assert not mount_phase['actual_project_compilation_started']
assert matching_phase['original_DiskArbitration_session_created'] and matching_phase['native_matching_callbacks']==11
assert not matching_phase['original_DiskArbitration_root_description_available']
assert power_phase['native_IORegisterForSystemPower_verified'] and power_phase['native_connection_subscription_cycles']==128
assert not power_phase['native_resume_notification_delivery_verified'] and not power_phase['full_xcode_build_ready']
assert disk_phase['original_configd_logging_abort_resolved'] and disk_phase['native_SystemConfiguration_store_checks']==16
assert not disk_phase['original_DiskArbitration_client_session_created']
assert current_phase['unrestricted_profile_attachment_verified'] and not current_phase['restrictive_profile_attachment_verified']
assert current_phase['diagnostic_fsevents_startup_abort_resolved'] and current_phase['diagnostic_mount_count']==0
abi=report('artifacts/native-crypto-private-abi-analysis.json');assert len(abi['legacy_CoreCrypto_exports_absent_from_current_native'])==28
for n in ['logs/native-crypto-xcode-live.resolved.log','logs/native-crypto-xcode-after-simulator.resolved.log','logs/cryptokit-original-aead-fault.gdb.log','logs/cryptokit-original-aead-fault.resolved.log','logs/native-volumes-next-stacks.gdb.log','logs/native-volumes-next-stacks.resolved.log','logs/filecoordination-original-disassembly.log','logs/cf-native-mounted-volume-enumerator-disassembly.log']:
    add(n)

archives={}
for n in ['artifacts/archive-crypto-history/manifest.json','artifacts/native-crypto-recorder-history/manifest.json','artifacts/crypto-token-parameters-source-history/manifest.json','artifacts/security-cryptokit-profile-history/manifest.json','artifacts/native-corecrypto-precondition-history/manifest.json']:
    d=read(n)
    for original,item in d.items():assert digest(item['archived'])==item['sha256'],(n,original)
    add(n);archives[n]=dict(sha256=digest(n),verified_files=len(d))
add('runtime/source-input-history/manifest.json')
for item in read('runtime/source-input-history/manifest.json').values():
    add(item['snapshot'],item['sha256'])
    for sha,path in item.get('revisions',{}).items():add(path,sha)
scripts=read('artifacts/native-crypto-recorder-guards.json')
assert len(scripts)==33
scripts+=['scripts/'+n for n in ['build-corecrypto-hkdf-source.py','build-corecrypto-boringssl.sh','corecrypto-hkdf-profile.py','test-corecrypto-hkdf.py','test-corecrypto-ctr.py','test-corecrypto-sha3.py','test-corecrypto-25519.py','build-corecrypto-malloc.py','corecrypto-original-profile.py','commoncrypto-original-profile.py','build-crypto-token-parameters.py','crypto-token-parameters-profile.py','build-security-cryptokit-constants.py','security-cryptokit-constants-profile.py','stage-crypto-token-kit-native.py','crypto-token-kit-native-profile.py','build-local-authentication-error.py','local-authentication-error-profile.py','probe-local-authentication-error.py','test-cryptokit-original.py','test-native-crypto-constants.py','test-native-crypto-regression.py','test-applearchive-native.py','probe-xcode-service-runtime.py','probe-native-volumes.py','probe-native-volumes-trace.py','device-identity-native-profile.py','mdns-native-profile.py','record-native-crypto-progress.py']]
scripts+=['scripts/record-iokitd-matching-progress.py','scripts/record-mount-flags-progress.py','scripts/record-s2c-lifecycle-progress.py','scripts/record-xpc-materialize-progress.py','scripts/record-mobileasset-query-progress.py','scripts/record-icu-signal-progress.py']
scripts+=['scripts/record-iokitd-power-progress.py','scripts/record-diskarbitration-progress.py']
scripts+=['scripts/record-unrestricted-sandbox-fsevents-progress.py','scripts/record-sandbox-fs-progress.py','scripts/validate-native-sandbox-policy-checkpoint.py','scripts/resolve-evidence-history.py']
scripts+=['scripts/'+n for n in ['fsevents-history-profile.py','test-fsevents-history.py','analyze-stat-cache-fsevents.py','record-fsevents-history-progress.py','fsevents-flush-profile.py','probe-xcode-service-runtime.py','resolve-evidence-history.py']]
scripts+=['scripts/'+n for n in ['build-corpse-map-server.py','stage-corpse-map-runtime.py','corpse-map-runtime-profile.py','test-corpse-map-errors.py','s2c-lifecycle-runtime-profile.py']]
for n in scripts:
    if n.endswith('.py'):ast.parse((root/n).read_text())
    add(n)
for n in ['README.md','config/cache-image-pins.json','bin/darling','bin/xcodebuild','scripts/runtime-ns.sh','artifacts/native-crypto-recorder-guards.json','artifacts/darling-corecrypto-sha3-25519-incremental.patch','fixtures/hello/native-crypto-constants.c','fixtures/hello/cryptokit-original.swift','fixtures/hello/cryptokit-original-owner.c','fixtures/hello/native-volumes.m']:
    add(n)
subprocess.run(['git','-C',str(root/'vendor/darling/src/external/corecrypto'),'apply','--reverse','--check',str(root/'artifacts/darling-corecrypto-sha3-25519-incremental.patch')],check=True)
sha='d6ceec0a4fa47e3f7a20c712d960ffb954b2246a2c94a0bf0818b2e8344065c5'
for n in ['runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild','runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild']:add(n,sha)
with (root/'runtime/session.lock').open('a') as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
next_work=[
    'Restore real Sandbox MAC policy application/enforcement: original CoreServices daemon now passes source directory initialization and original parameter creation/named SBPL compilation, but actual policy application returns ENOTSUP and the daemon exits 1 before bootstrap check-in. Stock compiler NULL parameters/stale errno were diagnosed and replaced by an executed original compiler, not a fabricated success.',
    'Restore original CoreServices/FileIDTree shared service and legacy volume-reference assignment. Live tracing now proves local root insertion succeeds but its legacy volume reference (+0x4c) remains zero and is filtered; the earlier empty-device-table hypothesis was incorrect. BSD APIs still expose 10 mounts while FileIDTree emits 0. Do not modify the field or skip the original filter.',
    'Make original NSFileManager/CF mounted-volume enumeration and original filecoordinationd functional; verify actual coordinated read/write behavior and exclusion, then retry the unchanged Xcode project. Current method owners are original Foundation/CoreFoundation/CarbonCore; the inactive Darling NSFileManager nil stub is not the selected implementation.',
    'Continue through real compilation, Unity/CocoaPods, archive, signing and export, preserving original CI commands. Audit the 28 missing legacy CoreCrypto private exports when exercised, hardware/auth services, CoreSimulator bootstrap, fsgetpath ENOTSUP and other previous gaps; no full-runtime or signing claim yet.'
]
next_work=icu_signal_phase['next_work']+['Audit the 28 missing legacy CoreCrypto private exports when exercised; signing, hardware/authentication and complete Xcode compilation remain unverified.']
next_work=fsevents_history_phase['next_work']+next_work[1:]
destination='artifacts/native-crypto-progress.json'
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),goal_status='active',complete=False,full_xcode_build_ready=False,signing_ready=False,default_entry_promoted=False,source_runtime=runtime,selected_original_libraries=selected,source_CoreCrypto_files=56,source_CoreCrypto_old_exports_preserved=402,source_crypto_comparison_cases=source_case_counts,native_crypto_comparison_cases=native_case_counts,native_invalid_null_preconditions_tested=False,native_error_output_zeroing_claimed=False,original_SDK_crypto_results=11,actual_native_CFString_values_verified=17,original_archive_payload_size=65537,authenticated_decryption_and_tamper_checks=True,original_CommonCrypto_CoreUtils_cases=852,CoreUtils_assertions=13385084,original_xcode_probes=probes,original_xcode_build_status_marker=132,build_wrapper_exit_status=-9,actual_project_compilation_started=False,original_filecoordinationd_selected=True,original_filecoordinationd_functional=False,stock_Darling_filecoordination_protocol_matches_original=False,native_mount_enumeration_functional=False,real_BSD_mount_count=10,original_FileIDTree_mount_count=0,original_CF_mount_enumerator_result=3,original_CF_mount_enumerator_error=dict(domain='NSCocoaErrorDomain',code=256),hardware_SecureEnclave_verified=False,LocalAuthentication_implemented=False,source_changes='Real SHA3-224/256/384/512, Curve25519/Ed25519 backed by pinned no-C++-runtime BoringSSL in the source candidate; selected execution now uses matched complete original Apple CoreCrypto/CommonCrypto/CryptoKit/C bridge/CryptoTokenKit, unchanged cryptographic calls, with a leaf-only original typed-allocator fallback. Genuine native-valued Security/token/auth constants added in Darling source. Original Xcode binary unchanged.',private_ABI_analysis=abi,fileidtree_directory_progress=directory_phase,native_sandbox_policy_progress=policy_phase,launchd_sandbox_progress=launchd_phase,sandbox_fs_progress=fs_phase,unrestricted_sandbox_fsevents_progress=current_phase,diskarbitration_log_compose_progress=disk_phase,iokitd_power_progress=power_phase,iokitd_matching_progress=matching_phase,mount_flags_progress=mount_phase,s2c_lifecycle_progress=s2c_phase,xpc_activation_materialize_progress=xpc_materialize_phase,mobileasset_query_progress=mobileasset_query_phase,icu_signal_progress=icu_signal_phase,current_candidate_runtime=icu_signal_phase['source_runtime'],archives=archives,evidence=evidence,scripts={n:digest(n) for n in scripts},next_work=next_work)
record.update(fsevents_history_progress=fsevents_history_phase,
              current_candidate_runtime=fsevents_history_phase['source_runtime'],
              latest_original_xcode_probes=fsevents_history_phase['original_xcode_regressions'],
              latest_original_project=fsevents_history_phase['original_xcode_regressions']['build'],
              latest_source_recursive_history_fsevents=fsevents_history_phase['source_fsevents'],
              previous_goal_turn_classification='progress',current_goal_turn_classification='progress',
              original_xcode_build_status_marker=65)
next_work=global_fsevents_phase['next_work']
record.update(global_fsevents_progress=global_fsevents_phase,current_candidate_runtime=global_fsevents_phase['source_runtime'],
              actual_project_compilation_started=True,original_macos_test_project_build_succeeded=True,
              ios_CocoaPods_project_build_succeeded=global_fsevents_phase['ios_CocoaPods_project_build_succeeded'],
              original_xcode_build_status_marker=global_fsevents_phase['ios_CocoaPods_native_exit_status'],build_wrapper_exit_status=global_fsevents_phase['ios_CocoaPods_wrapper_exit_status'],
              latest_original_project=global_fsevents_phase['ios_CocoaPods_project'] or global_fsevents_phase['original_macos_test_project'],
              next_work=next_work)
(root/destination).write_text(json.dumps(record,indent=2)+'\n')
state=read('artifacts/current-work-state.json');state.update(updated_at=record['checked_at'],primary_report=destination,goal_status='active',complete=False,working_changes_since_primary_report=False,latest_selected_runtime=runtime,latest_original_xcode_blocker='NSFileCoordinator blocked by mounted-volume/FileIDTree path: BSD reports 10 mounts; original FileIDTree reports 0; CF enumeration fails Cocoa 256; original daemon restarts',latest_xcode_loader_blocker=None,latest_xcode_failure_kind='FileIDTree_volume_enumeration_and_original_FileCoordination_service',latest_xcode_runtime_failure='Strict UTI, original version/SDK listing and original native crypto/archive tests pass. Original project remains blocked opening its coordinated project URL; build never reaches CompileC or SwiftCompile, wrapper ends -9 with status marker 132 during failed shutdown.',latest_sdk_listing_succeeded=True,latest_sdk_listing_attempted=True,latest_original_project_exit_status=132,latest_implementation_form=record['source_changes']+' Complete three-source Darling directory-helper repair; original Sandbox compiler/Match and 533 original profile resources restored privately. Original CoreServices named profile compiles, genuine enforcement still returns ENOTSUP.',latest_experimental_runtime=directory_phase['original_sandbox_resources']['source_runtime'],latest_experimental_coreservices=directory_phase['source_coreservices_directories'],latest_CoreServices_service_blocker='Original named SBPL compilation succeeds; actual Sandbox policy apply returns ENOTSUP; daemon exits 1 before bootstrap check-in',active_build=dict(task='original-cryptography-and-FileCoordination',running=False,report=destination),next_work=next_work)
new=['Direct complete Darling directory component source repair passes 156 checks; old source fails to create cache directory. Original CoreServices daemon progresses beyond actual directory initialization','Original Sandbox compiler/Match execute 2 valid and 2 invalid SBPL cases; 533 unchanged original resources allow original CoreServices named profile compilation; actual Sandbox enforcement still returns ENOTSUP','Live native root device exists with unassigned legacy volume reference +0x4c=0 and is filtered; previous empty-device-table hypothesis corrected','Matched original Apple CoreCrypto/CommonCrypto/CryptoKit/C bridge/CryptoTokenKit loads; 640 independent valid-input crypto cases pass in the original CoreCrypto and 640 in the source fallback','Original SDK client independently verifies 11 native P256/X25519/Ed25519/AESGCM/ChaCha/SHA256/SHA3/HMAC/HKDF results; authenticated error handling passes. Data slice startIndex preserved; no false index-0 assumption','Original AppleArchive compressed/encrypted streams pass with the original CryptoKit and matching CommonCrypto/CoreCrypto; wrong key and ciphertext corruption rejected','Native algorithm/token/auth identifiers: 17 real CFString values/type/length/copy checks pass; no hardware or authentication success fabricated','Original Xcode now reaches NSFileCoordinator/project opening; actual BSD mounted-volume APIs return 10 while original CarbonCore FileIDTree returns 0. Selected owners are original libraries; source NSFileManager nil stub is inactive']
state.setdefault('last_verification',[]).extend(v for v in new if v not in state['last_verification'])
state.update(latest_experimental_runtime=policy_phase['selected_runtime'],latest_sandbox_policy_progress='artifacts/native-sandbox-policy-progress.json',latest_sandbox_upload_decoding_verified=True,latest_sandbox_enforcement_verified=False,latest_CoreServices_service_blocker='Original named SBPL compiles and the original daemon uploads its 37-node policy to the actual server interpreter; attachment still returns ENOTSUP because operation hooks are not implemented; daemon exits 1 before bootstrap',active_build=dict(task='native-sandbox-policy-decoding-and-enforcement',running=False,report=destination))
state['next_work']=policy_phase['next_work']
policy_note='Original policy graph/FSA: 6034 semantic and 6488 parser/mutation checks pass ASan/UBSan; 29 real server uploads / 216 checks pass; unchanged coreservicesd uploads decoded 37-node policy but actual attachment/enforcement remains ENOTSUP'
if policy_note not in state.setdefault('last_verification',[]):state['last_verification'].append(policy_note)
state.update(latest_experimental_runtime=launchd_phase['source_runtime'],latest_launchd_sandbox_progress='artifacts/launchd-sandbox-progress.json',latest_launchd_sandbox_queries_enabled=True,latest_full_Mach_policy_enforcement_verified=False,active_verification=None,active_build=dict(task='launchd-sandbox-audit-query-paths',running=False,report=destination),next_work=next_work)
launchd_note='Complete 16-source launchd enables 11 audit-token Sandbox query sites and rejects query errors; 144 real Mach checks and 104 controlled negative-route checks pass. Original version, strict UTI and SDK listing with real preference/LaunchServices jobs pass; policy attachment/enforcement and project compilation remain incomplete.'
if launchd_note not in state['last_verification']:state['last_verification'].append(launchd_note)
state.update(latest_experimental_runtime=fs_phase['source_runtime'],latest_sandbox_fs_progress='artifacts/sandbox-fs-progress.json',latest_sandbox_file_mutation_query_sites=fs_phase['mutation_entrypoints'],latest_sandbox_enforcement_verified=False,active_build=dict(task='source-file-mutation-sandbox-query-hooks',running=False,report=destination),next_work=next_work)
fs_note='Full 878-source kernel adds pre-mutation Sandbox queries with pinned parents for mkdir/unlink/rmdir/rename; 338 real and 251 controlled checks pass, including 60 query events, no side effects on denial/errors and parent replacement. Quarantine, PID generation, XPC and original Xcode version/strict UTI/SDK listing pass; no complete policy attachment/enforcement or project compilation yet.'
if fs_note not in state['last_verification']:state['last_verification'].append(fs_note)
state.update(latest_selected_runtime=current_phase['source_runtime'],latest_experimental_runtime=current_phase['source_runtime'],
             latest_unrestricted_sandbox_fsevents_progress='artifacts/unrestricted-sandbox-fsevents-progress.json',
             latest_unrestricted_profile_attachment_verified=True,latest_restrictive_profile_attachment_verified=False,
             latest_coreservices_diagnostic_policy_only=True,latest_coreservices_diagnostic_alive=True,
             latest_coreservices_diagnostic_volume_count=0,
             latest_coreservices_diagnostic_blocker=current_phase['next_observed_diagnostic_failure'],
             latest_raw_fsevents_device_event_types=current_phase['raw_device_event_types'],
             latest_raw_fsevents_device_scope=current_phase['raw_device_scope'],
             latest_CoreServices_service_blocker='Original strict Sandbox profile still returns ENOTSUP. A separate explicit unrestricted diagnostic now reaches real bootstrap, system session and FSEvents initialization; DiskArbitration session creation fails and volume enumeration remains empty.',
             active_build=dict(task='source-legacy-fsevents-device-and-original-coreservices',running=False,report='artifacts/unrestricted-sandbox-fsevents-progress.json'),next_work=next_work)
current_note='Actual original Sandbox compile/apply/query/notify/fork/exec: 238 checks; unrestricted graph proof 228, existing semantic 6034 and parser 6488 pass. Linux raw FSEvents events pass 337 checks and Darling SDK device ABI passes 113; original daemon passes FSEvents initialization in explicit permissive-policy diagnostic. Three mount queries remain empty and original DiskArbitration session is null; full strict enforcement and compilation remain incomplete.'
if current_note not in state['last_verification']:state['last_verification'].append(current_note)
state.update(latest_selected_runtime=disk_phase['source_runtime'],latest_experimental_runtime=disk_phase['source_runtime'],
             latest_diskarbitration_progress='artifacts/diskarbitration-log-compose-progress.json',
             latest_log_composition_verified=True,latest_original_configd_IPC_verified=True,
             latest_original_DiskArbitration_session_verified=False,
             latest_original_DiskArbitration_failure=disk_phase['next_original_daemon_failure'],
             active_build=dict(task='original-configd-and-source-log-composition',running=False,report='artifacts/diskarbitration-log-compose-progress.json'),next_work=next_work)
disk_note='Source log send/compose passes 2295 checks including 192 original-wrapper ABI cases with replaced callees; existing pack 269 and hook 1642 regressions pass. Unchanged original configd reaches CFRunLoop and native SystemConfiguration set/read/remove plus actual Mach notification pass 16 checks. Original disk daemon creates a real Dynamic Store session, then exits 70 because IOPMrootDomain/system-power registration is missing. Full native logging parity, original restrictive Sandbox, volume enumeration, compilation and signing remain incomplete.'
if disk_note not in state['last_verification']:state['last_verification'].append(disk_note)
state.update(latest_selected_runtime=power_phase['source_runtime'],latest_experimental_runtime=power_phase['source_runtime'],
             latest_iokitd_power_progress='artifacts/iokitd-power-progress.json',
             latest_native_IORegisterForSystemPower_verified=True,
             latest_original_DiskArbitration_failure=power_phase['next_original_daemon_failure'],
             latest_native_resume_notification_delivery_verified=False,
             active_build=dict(task='source-iokitd-power-domain-and-Mach-IPC',running=False,report='artifacts/iokitd-power-progress.json'),
             active_verification=None,next_work=next_work)
state['last_verification'].append('Complete 22-source iokitd build: native power-domain lookup/open/interest subscription and 128 release cycles return actual daemon receive-port count from 14 to baseline 12. Seven mixed-port physical OOL cases cover empty/small/8 KiB boundary/large buffers; cross-task opens are rejected. Original disk daemon now passes power registration and exits 70 creating media-disappeared notification. Resume clock has 1016 ASan/UBSan model checks; actual resume callback delivery and pre-suspend barriers remain unverified/incomplete.') if not any('Complete 22-source iokitd build:' in v for v in state['last_verification']) else None
state.update(latest_selected_runtime=matching_phase['source_runtime'],latest_experimental_runtime=matching_phase['source_runtime'],
             latest_iokitd_matching_progress='artifacts/iokitd-matching-progress.json',
             latest_original_DiskArbitration_session_verified=True,
             latest_original_DiskArbitration_failure=matching_phase['current_observed_failure'],
             latest_Linux_media_discovery_verified=False,
             latest_notifyd_direct_Mach_transport_verified=True,
             latest_notifyd_XPC_matching_publisher_verified=False,
             active_build=dict(task='source-iokitd-matching-and-notifyd-transport',running=False,report='artifacts/iokitd-matching-progress.json'),
             active_verification=None,next_work=next_work)
matching_note='Complete 23-source iokitd and 6-source notifyd builds: actual native matching callbacks, initial enumeration/rearm/coalescing/deregistration, XML64/OOL, service lifetime, full Mach queue retry and all 128 notifier receive-port destructions verified using production objects with test-only services in a standalone harness. Native notify API passes 19 cross-process/reuse/cancel checks; power regression and original configd store pass. Original unchanged disk daemon now serves native DA sessions with and without debugger/default mode, but root description is NULL and no disks appear. Linux media, volumes, XPC matching publisher, complete project compilation and signing remain incomplete.'
if matching_note not in state['last_verification']:state['last_verification'].append(matching_note)
state.update(latest_selected_runtime=mount_phase['source_runtime'],latest_experimental_runtime=mount_phase['source_runtime'],
 latest_mount_flags_progress='artifacts/mount-flags-progress.json',
 latest_original_DiskArbitration_root_and_SystemRoot_description_verified_after_real_mount=True,
 latest_original_DiskArbitration_failure='Startup volume discovery remains incomplete; after real mount activity root and SystemRoot descriptions are available.',
 latest_kernel_mount_notifications_verified=True,latest_initial_existing_volume_discovery_verified=False,
 latest_original_xcode_blocker=mount_phase['current_observed_failure'],
 latest_original_project_exit_status=None,latest_original_project_wrapper_exit_status=mount_phase['original_xcode_probes']['build']['exit_status'],
 latest_xcode_runtime_failure='Strict UTI, original version and SDK listing pass. Original project times out before compilation with wrapper -9 and no returned xcodebuild status marker.',
 latest_CoreServices_service_blocker='Strict Sandbox policy application remains unsupported. Explicit permissive diagnostic with unchanged configd/diskarbitrationd/coreservicesd is alive; client acquires the real service port, but native FileIDTree still returns zero volumes and CF enumeration fails Cocoa 256.',
 active_build=dict(task='source-mount-flags-and-VFS-notifications',running=False,report='artifacts/mount-flags-progress.json'),active_verification=None,next_work=next_work)
mount_note='Complete 879-source kernel and 7-source notifyd: translated Linux/Darwin mount flags and canonical SystemRoot paths; 79 native checks, 137 ASan/UBSan parser checks and real namespace tmpfs mount/remount/unmount passed 34 checks with 11 original DA appearance callbacks. Root/SystemRoot descriptions now work after real mount activity. Native IPC/power/matching/FSEvents regressions pass. Native CoreServices port is available only in the separate permissive diagnostic; FileIDTree remains zero and CF returns Cocoa 256. Original project still does not compile.'
if mount_note not in state['last_verification']:state['last_verification'].append(mount_note)
state.update(latest_selected_runtime=s2c_phase['source_runtime'],latest_experimental_runtime=s2c_phase['source_runtime'],
 latest_s2c_lifecycle_progress='artifacts/s2c-lifecycle-progress.json',latest_original_xcode_blocker=s2c_phase['current_observed_failure'],
 latest_xcode_failure_kind='original_FileCoordination_RunningBoard_process_monitor_handshake',
 latest_xcode_runtime_failure='Source S2C lifecycle repair removes a verified dead-thread remote-mapping wait. Original strict UTI passes with real CoreServices/configd/disk daemon; original filecoordinationd receives the Xcode read claim and waits for absent com.apple.runningboard. No compiler steps run.',
 latest_CoreServices_service_blocker='Separate permissive diagnostic serves real legacy FS references and CF enumeration after native public API calls. Normal original-Xcode launch uses no API warmup. Strict Sandbox enforcement and complete startup enumeration remain incomplete.',
 latest_original_FileCoordination_claim_received=True,latest_original_FileCoordination_claim_granted=False,
 latest_original_project_wrapper_exit_status=s2c_phase['latest_original_project']['exit_status'],
 active_build=dict(task='source-S2C-lifecycle-and-original-FileCoordination',running=False,report='artifacts/s2c-lifecycle-progress.json'),active_verification=None,next_work=next_work)
s2c_note='Source server skips retained dead thread objects for remote VM calls, prefers live threads already in RPC, and rejects dead/terminating S2C entry. Old native CoreServices map was verified waiting for reply from dead target thread 62 in client process 52. Native UTI with original CoreServices now passes; original filecoordinationd receives actual Xcode project read claim but waits for absent RunningBoard handshake. Native legacy FS API calls assign real refs and restore CF enumeration of 10 mounts. Remote multithreaded mapping, 32 memory-entry cycles/concurrent maps, 128 power/matching release cycles and original version/SDK regressions pass. Complete project compilation remains unverified.'
if s2c_note not in state['last_verification']:state['last_verification'].append(s2c_note)
state.update(latest_selected_runtime=xpc_materialize_phase['source_runtime'],latest_experimental_runtime=xpc_materialize_phase['source_runtime'],
 latest_xpc_activation_materialize_progress='artifacts/xpc-activation-materialize-progress.json',latest_original_xcode_blocker=xpc_materialize_phase['current_observed_failure'],
 latest_xcode_failure_kind='MobileAsset_query_stub_leaks_original_Swift_downloadedAssets_continuation',
 latest_xcode_runtime_failure='Real XPC failure delivery lets original FileCoordination handle absent RunningBoard and grant/invoke actual project read claims. Real per-thread materialization state resolves original Foundation assertion. Original Xcode now reaches MAAssetQuery initWithType: stub and a leaked Swift continuation; no CompileC/SwiftCompile steps observed.',
 latest_original_FileCoordination_claim_received=True,latest_original_FileCoordination_claim_granted=True,
 latest_original_project_wrapper_exit_status=xpc_materialize_phase['latest_original_project']['exit_status'],
 latest_MobileAsset_query_implemented=False,latest_original_RunningBoard_handshake_failure_handled=True,
 latest_materialization_thread_policy_checks=1066,latest_materialization_process_policy_supported=False,
 active_build=dict(task='source-XPC-activation-and-thread-materialization',running=False,report='artifacts/xpc-activation-materialize-progress.json'),active_verification=None,next_work=next_work)
xpc_materialize_note='Complete 39-source libxpc preserves 630 exports/112 reexports; failed bootstrap activation now delivers invalidation and sync/async INVALID errors instead of indefinitely deferred sends. Existing 16 check-ins/256 replies, 33 cancellation lifecycles with 8 readers, 32 shmem lifecycles and 96 malformed packets pass. Complete 879-source kernel implements real per-thread DEFAULT/OFF/ON materialization state; 1066 checks include 8 isolated threads and 512 updates, invalid arguments and preserved errno. Original filecoordinationd grants and invokes two actual Xcode claims; original materialization assertion is gone. New blocker is source MAAssetQuery initWithType: stub leaking the original Swift downloadedAssets continuation. Process/ORIG policies, dataless providers and complete builds remain unsupported/unverified.'
if xpc_materialize_note not in state['last_verification']:state['last_verification'].append(xpc_materialize_note)
state.update(latest_selected_runtime=mobileasset_query_phase['source_runtime'],latest_experimental_runtime=mobileasset_query_phase['source_runtime'],
 latest_mobileasset_query_progress='artifacts/mobileasset-query-progress.json',latest_source_mobileasset_query=mobileasset_query_phase['source_mobileasset_query'],
 latest_original_xcode_blocker=mobileasset_query_phase['current_observed_failure'],latest_xcode_failure_kind='original_input_option_condition_wait_with_SwiftPM_subprocess_CoreSimulator_and_SecurityServer_waits',
 latest_xcode_runtime_failure=mobileasset_query_phase['current_observed_failure'],latest_MobileAsset_query_implemented=True,latest_MobileAsset_download_implemented=False,
 latest_original_project_wrapper_exit_status=mobileasset_query_phase['latest_original_project']['exit_status'],latest_mobileasset_query_native_checks=1823,
 latest_original_MobileAsset_continuation_leak_resolved=True,active_build=dict(task='source-MobileAsset-query-and-original-project-waits',running=False,report='artifacts/mobileasset-query-progress.json'),active_verification=None,next_work=next_work)
query_note='Complete 15-source MobileAsset implements real keyed XPC queries and typed sync/async completion, secure results/metadata and original asset state values. 1823 native checks cover 48 actual query replies, 4 concurrent threads/32 async queries, 8 detached callbacks, absent-service errors and malformed replies. Both previous Pallas wire regressions pass. Original Xcode handles genuine Metal asset query failure without leaking its Swift continuation. Main thread remains in input-option condition wait; correctly symbolicated live stacks show SwiftPM deriveMetalToolchainPath subprocess waits, CoreSimulator service loading and SecurityServer verifyPrivileged2. Direct causality, actual compilation, daemon/catalog/downloads and signing remain unverified.'
if query_note not in state['last_verification']:state['last_verification'].append(query_note)
state.update(latest_selected_runtime=icu_signal_phase['source_runtime'],latest_experimental_runtime=icu_signal_phase['source_runtime'],
 latest_icu_signal_progress='artifacts/icu-signal-progress.json',latest_experimental_runtime_wrapper=icu_signal_phase['experimental_runtime_wrapper'],
 latest_original_xcode_blocker=icu_signal_phase['current_observed_failure'],latest_xcode_failure_kind='original_ClangStatCache_missing_FSEventsGetCurrentEventId_from_CoreServices',
 latest_xcode_runtime_failure=icu_signal_phase['current_observed_failure'],latest_original_project_wrapper_exit_status=icu_signal_phase['latest_original_project']['exit_status'],
 latest_original_project_returned=True,latest_original_SwiftBuild_service_started=True,latest_original_build_description_created=True,latest_original_build_tasks_executed=True,
 latest_ICU_native_checks=157,latest_real_fatal_child_exits_tested=8,latest_fatal_signals_to_parent_and_sibling=0,
 latest_original_system_version_bound_privately=True,latest_persistent_SystemVersion_unchanged=True,
 active_build=dict(task='source-fatal-signals-matching-ICU-and-original-SwiftBuild',running=False,report='artifacts/icu-signal-progress.json'),active_verification=None,next_work=next_work)
icu_note='Actual previous failure was a SIGSEGV at 0x8 in original CF number-formatting during SwiftPM RSA certificate import, then source sigexc kill(0,SIGSEGV) killed the parent group and hid the Xcode exit. Matching original ICU 78 data resolves native formatter NULL; 157 checks cover 36 number roundtrips/four locales and actual OpenSSL RSA signature/tamper verification. Full 879-source kernel targets self for default fatal signals/abort; eight real child deaths leave parent and sibling unaffected. Private reference SystemVersion binding fixes unparseable Darling build ID without changing persistent metadata/default launchers. Original OSLog/Swift overlay allow real SWBBuildService dependency graph/build description and directory/header-map/response tasks; nine output files archived. Original project now returns 65 because clang-stat-cache lacks FSEventsGetCurrentEventId in CoreServices. No source CompileC/link, full Unity/CocoaPods or signing completion.'
if icu_note not in state['last_verification']:state['last_verification'].append(icu_note)
state.update(latest_fsevents_history_progress='artifacts/fsevents-history-progress.json',
 latest_selected_runtime=fsevents_history_phase['source_runtime'],latest_experimental_runtime=fsevents_history_phase['source_runtime'],
 latest_source_recursive_history_fsevents=fsevents_history_phase['source_fsevents'],
 latest_original_project=fsevents_history_phase['original_xcode_regressions']['build'],
 latest_fsevents_native_recursive_history_checks=fsevents_history_phase['native_recursive_history_checks'],
 latest_original_xcode_blocker=fsevents_history_phase['current_observed_failure'],
 latest_fsevents_global_event_ids_implemented=False,
 latest_original_project_exit_status=fsevents_history_phase['original_xcode_regressions']['build']['exit_status'],
 latest_original_project_wrapper_exit_status=fsevents_history_phase['original_xcode_regressions']['build']['exit_status'],
 active_build=dict(task='source-recursive-fsevents-and-explicit-history-loss',running=False,report='artifacts/fsevents-history-progress.json'),
 active_verification=None,next_work=next_work)
state.update(objective='将 xcodebuild 的命令行在 darling 环境下完整运行起来，可以用 xcodebuild 成功编译并签名带 cocoapods 的 unity/ue 游戏引擎生成的项目, ios target 为重点',
 latest_global_fsevents_progress='artifacts/global-fsevents-progress.json',latest_selected_runtime=global_fsevents_phase['source_runtime'],latest_experimental_runtime=global_fsevents_phase['source_runtime'],
 latest_fsevents_global_event_ids_implemented=True,latest_original_xcode_blocker=global_fsevents_phase['current_observed_failure'],
 actual_project_compilation_started=True,original_macos_test_project_build_succeeded=True,
 ios_CocoaPods_project_build_succeeded=global_fsevents_phase['ios_CocoaPods_project_build_succeeded'],
 latest_original_project=record['latest_original_project'],latest_xcode_runtime_failure=global_fsevents_phase['current_observed_failure'],
 latest_original_project_exit_status=global_fsevents_phase['ios_CocoaPods_native_exit_status'],latest_original_project_wrapper_exit_status=global_fsevents_phase['ios_CocoaPods_wrapper_exit_status'],
 active_build=dict(task='original-xcode-ios-cocoapods-build-and-signing',running=False,report='artifacts/global-fsevents-progress.json'),next_work=next_work)
(root/'artifacts/current-work-state.json').write_text(json.dumps(state,indent=2)+'\n')
print('Recorded',len(evidence),'current hashes,',len(scripts),'scripts; macOS project builds; full iOS/engine/signing goal remains active.')
