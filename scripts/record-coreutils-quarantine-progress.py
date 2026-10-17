#!/usr/bin/env python3
"""Record actual crypto/runtime execution and the retained native policy gate."""

# Preserve the newer native cryptography and FileCoordination checkpoint.
from pathlib import Path as _nc_Path
import json as _nc_json
_nc_state = _nc_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _nc_state.exists() and _nc_json.loads(_nc_state.read_text()).get('primary_report') == 'artifacts/native-crypto-progress.json':
    print('Preserving the newer native cryptography checkpoint'); raise SystemExit(0)

# Historical recorders must preserve the newer archive/crypto checkpoint.
from pathlib import Path as _ac_Path
import json as _ac_json
_ac_state = _ac_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _ac_state.exists() and _ac_json.loads(_ac_state.read_text()).get('primary_report') == 'artifacts/archive-crypto-progress.json':
    print('Preserving the newer archive/crypto checkpoint'); raise SystemExit(0)

# Historical recorders must preserve the newer dispatch/XPC checkpoint.
from pathlib import Path as _dx_Path
import json as _dx_json
_dx_state = _dx_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _dx_state.exists() and _dx_json.loads(_dx_state.read_text()).get('primary_report') == 'artifacts/dispatch-xpc-progress.json':
    print('Preserving the newer dispatch/XPC checkpoint'); raise SystemExit(0)

# A historical recorder must not replace the newer active checkpoint.
from pathlib import Path as _cw_Path
import json as _cw_json
_cw_state = _cw_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _cw_state.exists() and _cw_json.loads(_cw_state.read_text()).get('primary_report') == 'artifacts/cryptex-workqueue-progress.json':
    print('Preserving the newer Cryptex/workqueue checkpoint'); raise SystemExit(0)
# A historical recorder must not replace the current validated runtime state.
from pathlib import Path as _qvf_Path
import json as _qvf_json
_qvf_state = _qvf_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _qvf_state.exists() and _qvf_json.loads(_qvf_state.read_text()).get('primary_report') in {'artifacts/quarantine-vfs-progress.json','artifacts/device-identity-progress.json'}:
    print('Preserving the newer Quarantine VFS checkpoint'); raise SystemExit(0)
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
read=lambda n:json.loads((root/n).read_text())
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
p=runpy.run_path(str(root/'scripts/crypto-quarantine-runtime-profile.py'))['profile']()
runtime=p['source_runtime'];stage=p['source_crypto_quarantine'];crypto=p['source_coreutils_crypto']
assert crypto['full_CoreUtils_source_build'] and crypto['complete_source_files']==132
assert crypto['original_exports_preserved']==1429 and len(crypto['added_exports'])==4
assert not crypto['other_preexisting_CoreUtils_stubs_implemented']
assert stage['full_quarantine_source_files']==2 and len(stage['proc_exports'])==22
assert stage['original_quarantine_exports_preserved']==28 and not stage['policy_calls_implemented']
for key,item in runtime.items():
    assert digest(item['path'])==item['sha256']
    if key!='LINUXCODE_QUARANTINE':assert item['sha256']==stage['previous_source_runtime'][key]['sha256']
native=read(stage['native_reconstruction']);assert not native['modern_adapter'] and not native['backend_call_overrides']
assert set(native['redirected_imports'])=={'_malloc_type_malloc','_malloc_type_calloc'}
assert digest('runtime/fullsystem-libraries/usr/lib/system/libquarantine.dylib')==native['original_image_sha256']
evidence=[]
def add(n):assert (root/n).is_file(),n;evidence.append(n)
def checked_test(name,marker):
    data=read(name);assert data['source_runtime']==runtime and data['exit_status']==0
    assert data['source_coreutils_crypto']['library_sha256']==crypto['library_sha256']
    for key in ['source','binary','log']:assert digest(data[key])==data[key+'_sha256'];add(data[key])
    assert marker in (root/data['log']).read_text();add(name);return data
test=checked_test('artifacts/coreutils-crypto-source-test.json','cases=852 hash=48 hmac=480 hkdf=324 checks=13385084')
assert test['independent_crypto_vectors_verified'];assert digest(test['vectors'])==test['vectors_sha256'];add(test['vectors'])
proc=checked_test('artifacts/quarantine-proc-native-test.json','checks=797')
assert proc['native_proc_value_execution_verified'] and not proc['policy_application_verified']
assert 'NATIVE_QUARANTINE_REAL_APPLY_RESULT result=45 errno=45' in (root/proc['log']).read_text()
old=read('artifacts/coreutils-crypto-source-old-control.json');assert old['exit_status']!=0 and old['old_CoreUtils_missing_new_crypto_API_confirmed']
assert digest(old['log'])==old['log_sha256'];add(old['log']);add('artifacts/coreutils-crypto-source-old-control.json')
regression=read('artifacts/crypto-quarantine-regression.json');assert regression['source_runtime']==runtime
assert regression['source_coreutils_crypto']['library_sha256']==crypto['library_sha256']
assert len(regression['checks'])==5 and all(row['exit_status']==0 for row in regression['checks'])
for row in regression['checks']:
    for key in ['log','binary']:assert digest(row[key])==row[key+'_sha256'];add(row[key])
add('artifacts/crypto-quarantine-regression.json')
failure=read('artifacts/quarantine-proc-first-clone-failure.json');assert failure['exit_status']!=0
for key in ['source','binary','log']:assert digest(failure[key])==failure[key+'_sha256'];add(failure[key])
assert digest(failure['core_diagnostic'])==failure['core_diagnostic_sha256'];add(failure['core_diagnostic']);add('artifacts/quarantine-proc-first-clone-failure.json')
core=read(failure['core_diagnostic']);assert digest(core['log'])==core['log_sha256'];add(core['log'])
assert any(row.get('nearest_symbol')=='__qtn_proc_clone' for row in core['frames'])
abi=read('artifacts/coreutils-crypto-native-abi.json');assert digest(abi['image'])==abi['image_sha256']
assert digest(abi['native_disassembly'])==abi['native_disassembly_sha256'];add(abi['native_disassembly']);add('artifacts/coreutils-crypto-native-abi.json')
assert [(abi['descriptors'][n]['digest_size'],abi['descriptors'][n]['block_size']) for n in ['SHA1','SHA256','SHA512']]==[(20,64),(32,64),(64,128)]
assert abi['hash_context_bytes']==216 and abi['HMAC_context_bytes']==344
names=[
 'artifacts/xcode-service-runtime-crypto-mobile-generation-policy-expected-sandbox-typed-cloud-base-prefs-daemon-version.json',
 'artifacts/xcode-service-runtime-crypto-mobile-generation-policy-expected-sandbox-typed-cloud-prefs-daemon-diagnostic-build.json',
 'artifacts/xcode-service-runtime-crypto-extended-mobile-generation-policy-expected-sandbox-typed-cloud-prefs-daemon-diagnostic-build.json',
]
probes={};original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
original_sha=digest(original);assert original_sha==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
assert original_sha=='d6ceec0a4fa47e3f7a20c712d960ffb954b2246a2c94a0bf0818b2e8344065c5'
for name in names:
    data=read(name);assert data['source_runtime']==runtime and data['original_xcodebuild_sha256']==original_sha
    for key in ['log','script']:assert digest(data[key])==data[key+'_sha256'];add(data[key])
    for n,sha in data['service_logs'].items():assert digest(n)==sha;add(n)
    for job in data['jobs']:assert digest(job['path'])==job['sha256'];add(job['path'])
    assert digest('scripts/runtime-ns.sh')==data['runtime_namespace_script_sha256']
    service=data['original_preference_service'];assert digest(service['original'])==service['sha256']==digest(service['selected'])
    assert not data['UTI_preflight_verified'] and data['exit_status']!=0
    text=(root/data['log']).read_text();assert 'Symbol not found: _kCryptoHashDescriptor_SHA512' not in text
    daemon=next(n for n in data['service_logs'] if n.endswith('-cfprefsd-daemon.log'))
    assert 'Failure to configure quarantine: qtn_proc_apply_to_self() failed. Exiting daemon.' in (root/daemon).read_text()
    assert 'Symbol not found: __qtn_proc_alloc' not in (root/daemon).read_text()
    probes[name]=dict(exit_status=data['exit_status'],strict_UTI_verified=False,diagnostic_without_UTI_preflight=data['diagnostic_without_UTI_preflight'],returned_status_marker=data.get('xcode_process_returned',False),live_observations=len(data.get('xcode_live_observations',[])));add(name)
observed=read(names[-1]);assert observed['xcode_process_started'] and observed['xcode_invocation_attempted'] and not observed['xcode_process_returned']
assert len(observed['xcode_live_observations'])==1
assert observed['diagnostic_without_UTI_preflight'] and observed['xcode_arguments'][-1]=='build'
seen=read('artifacts/crypto-quarantine-xcode-live-observation.json');assert seen['actual_xcode_process_seen']
for n,sha in seen['artifacts'].items():assert digest(n)==sha;add(n)
add('artifacts/crypto-quarantine-xcode-live-observation.json')
analysis=read('artifacts/Quarantine-policy-next-analysis.json');assert analysis['cfprefsd_requested_flags']==6 and not analysis['policy_implementation_complete']
for key in ['disassembly','cfprefsd_entry_disassembly']:assert digest(analysis[key])==analysis[key+'_sha256'];add(analysis[key])
add('artifacts/Quarantine-policy-next-analysis.json')
kext=read(analysis['collection_evidence']);assert digest(kext['collection'])==kext['collection_sha256'];assert digest(kext['inspection_image'])==kext['inspection_image_sha256'];add(analysis['collection_evidence'])
assert kext['entry']['id']=='com.apple.security.quarantine'
history=read('artifacts/expected-sandbox-runtime-history/manifest.json')
for item in history.values():assert digest(item['archived'])==item['sha256']
add('artifacts/expected-sandbox-runtime-history/manifest.json')
patch='artifacts/darling-coreutils-crypto-source.patch';subprocess.run(['git','apply','--reverse','--check',str(root/patch)],cwd=root/'vendor/darling',check=True);add(patch)
for name in ['artifacts/coreutils-crypto-source-build.json','artifacts/crypto-quarantine-runtime-stage.json',stage['native_reconstruction'],stage['native'],stage['native_provider'],'artifacts/typed-malloc-source-stage.json','logs/crypto-quarantine-runtime-stage-driver.log','logs/coreutils-crypto-source-build-driver.log']:add(name)
scripts=['scripts/'+n for n in ['build-coreutils-crypto-source.py','stage-crypto-quarantine-runtime.py','crypto-quarantine-runtime-profile.py','test-coreutils-crypto-source.py','test-quarantine-proc-native.py','test-crypto-quarantine-regression.py','probe-xcode-service-runtime.py','record-coreutils-quarantine-progress.py']]
next_work=[
 'Implement the real Quarantine process/file policy required by cfprefsd flags 6. The original Intel kext and its syscall/create/exec functions are recovered locally. Validate actual label lifetime, inherited state, file propagation and enforcement; do not acknowledge application with memory-only state or unconditional success. Then restore cfprefsd, strict UTI and normal original Xcode initialization.',
 'Continue the original xcodebuild project build after real preference-service initialization. The latest diagnostic executes original libxcodebuildLoader and DVTFoundation and now waits inside CoreFoundation system preferences; it is not a build/SDK-listing/signing success. Retain other lazy loader/runtime gaps until executed.',
 'Preserve the native Quarantine unset-pattern clone failure. The valid-pattern object/metadata/clone tests pass, but NULL-pattern cloning reaches strdup/strlen and faults in the current runtime; native-OS equivalence is unproven.',
 'Complete earlier chained-fixup strong replacement coalescing, actual Security NSXPC, and the original Unity/CocoaPods compilation, archive, signing and export. The default launcher is not promoted until full execution is proven.'
]
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),previous_report='artifacts/expected-sandbox-runtime-progress.json',previous_evidence_archive='artifacts/expected-sandbox-runtime-history/manifest.json',previous_goal_turn_classification='progress',current_goal_turn_classification='progress',source_runtime=runtime,CoreUtils_source_files=132,CoreUtils_old_exports_preserved=1429,CoreUtils_crypto_vectors=852,CoreUtils_crypto_guard_checks=13385084,Quarantine_source_files=2,Quarantine_old_exports_preserved=28,Quarantine_native_proc_exports=22,Quarantine_valid_object_checks=797,Quarantine_policy_application_implemented=False,Quarantine_unset_pattern_clone_compatible=False,strict_UTI_verified=False,diagnostic_original_xcode_execution_positively_verified=True,diagnostic_skips_UTI_preflight=True,diagnostic_runtime_wait='CoreFoundation synchronous system cfprefsd reply during original libxcodebuildLoader/DVTFoundation initialization',original_xcodebuild_sha256=original_sha,probe_results=probes,default_launcher_changed=False,default_launcher_sha256=digest('bin/xcodebuild'),full_xcode_build_ready=False,signing_ready=False,complete=False,goal_status='active',next_work=next_work,evidence={n:digest(n) for n in dict.fromkeys(evidence)},scripts={n:digest(n) for n in scripts})
destination='artifacts/coreutils-quarantine-progress.json';temporary=root/(destination+'.pending');temporary.write_text(json.dumps(record,indent=2)+'\n');temporary.replace(root/destination)
state=read('artifacts/current-work-state.json');state.update(updated_at=record['checked_at'],primary_report=destination,goal_status='active',complete=False,latest_selected_runtime=runtime,latest_xcode_loader_blocker=None,latest_staged_coreml_and_metal_blocker='System cfprefsd reply wait after the latest loader gaps (diagnostic without UTI preflight)',latest_xcode_runtime_failure='Actual original Xcode/loader/DVTFoundation now execute and wait in CFPreferences. The genuine cfprefsd daemon loads but exits because Quarantine policy application returns ENOTSUP. No full compilation or signing completed.',latest_xcode_failure_kind='Quarantine_policy_required_by_CFPrefs',latest_implementation_form='Complete source CoreUtils framework with real Hash/HMAC/HKDF; complete two-file source Quarantine library retaining old exports and explicitly reexporting 22 actual native process APIs; original Xcode and CI/project arguments unchanged. No policy or signing success fabricated.',active_build={'task':'source-CoreUtils-native-Quarantine-runtime','running':False,'report':destination})
state['next_work']=next_work
state.setdefault('source_components',{}).update(CoreUtils_crypto='artifacts/coreutils-crypto-source-build.json',native_Quarantine_proc='artifacts/crypto-quarantine-runtime-stage.json',CoreUtils_Quarantine_progress=destination)
state['latest_validation_reports']=list(dict.fromkeys(state.get('latest_validation_reports',[])+list(record['evidence'])+[destination]))
temporary=root/'artifacts/current-work-state.json.pending';temporary.write_text(json.dumps(state,indent=2)+'\n');temporary.replace(root/'artifacts/current-work-state.json')
print('Recorded real source crypto/native objects, positive original Xcode initialization and retained Quarantine policy gate; full goal remains active')
