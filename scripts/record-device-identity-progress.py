#!/usr/bin/env python3
"""Record original dependency execution and the retained Cryptex/crypto analysis gap."""

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
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,runpy,subprocess
root=Path(__file__).resolve().parent.parent
read=lambda n:json.loads((root/n).read_text())
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
p=runpy.run_path(str(root/'scripts/device-identity-native-profile.py'))['profile']();runtime=p['source_runtime'];stage=p['native_device_identity'];evidence={}
def add(n):evidence[n]=digest(n)
def pair(d,k):assert digest(d[k])==d[k+'_sha256'],d[k];add(d[k])
for n,sha in {**stage['originals'],**stage['files'],**stage['dependencies']}.items():
    assert digest(n)==sha,n;add(n)
for n,target in stage['symlinks'].items():assert os.readlink(root/n)==target
pair(stage,'reconstruction');pair(stage,'alias_reference');add('artifacts/device-identity-native-stage.json')
assert not stage['backend_overrides'] and not stage['device_attestation_verified']
reports=[stage['reconstruction'],*stage['dependencies']];assert len(reports)==4
assert sum(read(n)['exports'] for n in reports)==402
for name in reports:
    d=read(name);assert not d['modern_adapter'] and not d['backend_call_overrides'] and not d['redirected_imports'];add(name)
for item in runtime.values():assert digest(item['path'])==item['sha256']
parent=read('artifacts/quarantine-vfs-runtime-stage.json');assert parent['source_runtime']==runtime
add('artifacts/quarantine-vfs-runtime-stage.json')

builds=['artifacts/iokit-main-port-source-build.json','artifacts/security-device-constant-build.json','artifacts/crypto-token-error-source-build.json']
for name in builds:
    d=read(name)
    for key in ['source','source_header','source_list','native_disassembly','native_image','framework','backend','constant_source','component','library','base','reference','thin_base']:
        if key in d:pair(d,key)
    add(name)
assert not read(builds[0])['full_IOKit_source_build']
assert not read(builds[1])['full_Security_source_build'] and not read(builds[1])['attestation_service_implemented']
assert not read(builds[2])['full_CryptoTokenKit_source_build'] and not read(builds[2])['existing_token_service_stubs_implemented']
for name in ['artifacts/security-anonymous-attestation-constant-reference.json','artifacts/crypto-token-error-native-reference.json']:
    d=read(name);pair(d,'provider');add(name)
assert read(builds[1])['value']=='2147483680' and read(builds[2])['value']=='CryptoTokenKit'
for n in ['vendor/darling/src/external/IOKitUser/IOKitLib.c','vendor/darling/src/external/security/keychain/headers/SecItemPriv.h','vendor/darling/src/external/security/OSX/sec/Security/SecExports.exp-in']:add(n)
assert '_kSecAttrKeyTypeSecureEnclaveAnonymousAttestation' in (root/'vendor/darling/src/external/security/OSX/sec/Security/SecExports.exp-in').read_text()

for variant in ['', 'image4-', 'eager-control-']:
    name='artifacts/device-identity-native-'+variant+'load.json';d=read(name)
    pair(d,'stage');pair(d,'runtime')
    for key in ['source','binary','log']:pair(d,key)
    for n,sha in d['source_components'].items():assert digest(n)==sha;add(n)
    if variant=='eager-control-':
        assert d['expected_negative_control_verified'] and not d['native_dlopen_verified'] and d['exit_status']==1
        assert 'Symbol not found: _SecKeyCopySystemKey' in (root/d['log']).read_text()
        control=read('runtime/rebuilt-device-identity-eager-control/reconstruction.json');assert control['lazy_bindings']==0 and not control['backend_call_overrides']
    else:
        assert d['native_dlopen_verified'] and d['exit_status']==0
        assert 'NATIVE_FOUNDATION_DLOPEN_COMPLETED' in (root/d['log']).read_text()
    assert not d['device_attestation_verified'];add(name)
components=read('artifacts/device-loader-source-components-test.json')
assert components['real_backend_forwarding_and_constant_values_verified'] and components['exit_status']==0
for key in ['source','binary','log','IOKit_source_report','Security_constant_report','token_constant_report']:pair(components,key)
text=(root/components['log']).read_text();assert 'bootstrap=0 modern=0 legacy=0' in text and 'modern=268435459 legacy=268435459' in text
add('artifacts/device-loader-source-components-test.json')
regression=read('artifacts/device-identity-regression.json');assert regression['source_runtime']==runtime and regression['native_device_identity']==stage
assert len(regression['checks'])==6
for row in regression['checks']:
    assert row['exit_status']==0
    for key in ['binary','log']:pair(row,key)
assert 'cases=852 hash=48 hmac=480 hkdf=324 checks=13385084' in (root/regression['checks'][-1]['log']).read_text()
add('artifacts/device-identity-regression.json')

probes={}
for mode in ['version','showsdks','build']:
    stem='xcode-service-runtime-device-vfs-crypto-'+('extended-' if mode!='build' else '')+'mobile-generation-policy-expected-sandbox-typed-cloud'+('-base' if mode=='version' else '')+'-prefs-daemon-'+mode
    name='artifacts/'+stem+'.json';d=read(name);assert d['source_runtime']==runtime and d['native_device_identity']==stage
    assert d['UTI_preflight_verified'] and not d['diagnostic_without_UTI_preflight']
    assert d['xcode_process_started'] and d['xcode_invocation_attempted'] and d['xcode_process_returned']
    assert d['exit_status']==(70 if mode=='build' else 0)
    for key in ['log','script']:pair(d,key)
    for n,sha in d['service_logs'].items():assert digest(n)==sha;add(n)
    for job in d['jobs']:assert digest(job['path'])==job['sha256'];add(job['path'])
    for n,sha in d['prefix_accounts_unchanged'].items():assert digest(n)==sha
    daemon=next(n for n in d['service_logs'] if n.endswith('-cfprefsd-daemon.log'));log=(root/daemon).read_text();assert 'sent a request related to' in log and 'successfully sent' in log and 'Failure to configure quarantine' not in log
    text=(root/d['log']).read_text()
    if mode=='version':assert 'Xcode 26.6' in text and 'Build version 17F113' in text
    elif mode=='showsdks':assert 'iOS SDKs:' in text and 'macOS SDKs:' in text and '-sdk iphoneos26.5' in text
    else:
        assert 'Library not loaded: /usr/lib/libcryptex.dylib' in text
        assert 'Library not loaded: /usr/lib/libimg4.dylib' not in text
        assert 'Library not loaded: /System/Library/PrivateFrameworks/DeviceIdentity.framework' not in text
    service=d['original_preference_service'];assert digest(service['original'])==service['sha256']==digest(service['selected'])
    probes[mode]=dict(report=name,exit_status=d['exit_status'],strict_UTI=True,original_process_returned=True);add(name)

reference=read(stage['alias_reference']);assert reference['Apple_chunklist_verification_passed'] and reference['system_version']['ProductBuildVersion']=='24E263'
for key in ['recovery_image','chunklist','listing']:pair(reference,key)
assert list(reference['extracted_symlinks'].values())==['./libimage4.dylib']
for n,target in reference['extracted_symlinks'].items():assert os.readlink(root/n)==target
search=read('artifacts/img4-reference-search.json');assert len(search['payloads_completed'])==53 and not search['found_libimg4']
for key in ['installer_config','guest_script','log']:pair(search,key)
for n,sha in search['evidence'].items():assert digest(n)==sha;add(n)
add('artifacts/img4-reference-search.json');add('artifacts/core-simulator-utilities-img4-imports.json')
analysis=read('artifacts/device-identity-next-analysis.json');assert not analysis['crypto42_library_emitted'] and not analysis['crypto42_library_selected']
assert not (root/'runtime/rebuilt-crypto42-device-native/libcrypto.42.dylib').exists()
assert len(read('runtime/rebuilt-crypto42-device-native/unclassified-code-imports.json'))==58
assert len(read('runtime/rebuilt-crypto42-device-native/unsupported-code.json'))==49
for n,sha in analysis['evidence'].items():assert digest(n)==sha;add(n)
for item in analysis['candidate_original_images'].values():pair(item,'report');assert not item['selected']
assert not any('libcryptex' in n or 'libcrypto.42' in n for n in stage['files'])
upstream=read(analysis['upstream_assembly_reference']);pair(analysis,'upstream_assembly_reference');pair(upstream,'archive')
for n,sha in upstream['extracted_files'].items():assert digest(n)==sha;add(n)
add('artifacts/device-identity-next-analysis.json')

history_name='artifacts/quarantine-vfs-history/manifest.json';history=read(history_name)
for n,row in history.items():assert digest(row['archived'])==row['sha256']
old=read(history['artifacts/quarantine-vfs-progress.json']['archived']);assert old['source_runtime']==runtime
add(history_name)
for repo,label in [('vendor/darling/src/external/IOKitUser','darling-iokit-main-port-source'),('vendor/darling/src/external/security','darling-security-device-constant-source'),('vendor/darling','darling-crypto-token-error-source')]:
    name='artifacts/'+label+'.patch';subprocess.run(['git','apply','--reverse','--check',str(root/name)],cwd=root/repo,check=True);subprocess.run(['git','diff','--check'],cwd=root/repo,check=True);add(name)
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild';original_sha=digest(original)
assert original_sha==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')=='d6ceec0a4fa47e3f7a20c712d960ffb954b2246a2c94a0bf0818b2e8344065c5'
assert digest('bin/xcodebuild')==old['default_launcher_sha256']
add('README.md');add('config/cache-image-pins.json');add('scripts/runtime-ns.sh')
scripts=['scripts/'+n for n in ['build-iokit-main-port-source.py','build-security-device-constant.py','build-crypto-token-error-source.py','stage-device-identity-native.py','device-identity-native-profile.py','probe-device-identity-native.py','test-device-loader-source-components.py','test-device-identity-regression.py','probe-xcode-service-runtime.py','rebuild-c-cache-image.py','cache-code-analysis.py','extract-img4-reference-guest.sh','download-img4-recovery.py','inspect-img4-older-recovery.py','record-device-identity-progress.py','record-quarantine-vfs-progress.py']]
scripts+=read('artifacts/quarantine-vfs-recorder-guards.json')
next_work=[
    analysis['next_action'],
    'Validate actual Cryptex and CoreSimulatorUtilities loading, continue every required original Xcode plugin and the unchanged project build; no plugin suppression or fake service/signing acknowledgements.',
    'Keep the real missing SecKeyCopySystemKey SPI and existing CryptoTokenKit token-service stubs explicit. Native DeviceIdentity/Image4 loading does not prove attestation or firmware verification.',
    'Investigate earlier lsd lifecycle exit 139, C++ chained-fixup strong replacement and production Security NSXPC failures when needed; preserve the source Quarantine subset limitations.',
    'Complete original Unity/CocoaPods compilation, archive, genuine signing and export, then integrate the default CI entry only after full execution is verified.'
]
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),previous_goal_turn_classification='progress',current_goal_turn_classification='progress',previous_evidence_archive=history_name,source_runtime=runtime,selected_original_images=4,selected_original_exports=402,IOKit_real_source_entry_and_backend_port_execution_verified=True,native_Security_and_Token_constant_values_verified=True,DeviceIdentity_native_loading_verified=True,Image4_native_alias_loading_verified=True,unimplemented_Security_SPI_retained_in_eager_control=True,strict_UTI_verified=True,original_xcode_version_verified=True,original_xcode_SDK_listing_verified=True,original_project_build_exit_status=70,current_build_failure='CoreSimulatorUtilities requires libcryptex.dylib. Cryptex/AuthInstall candidates exist, but libcrypto.42 reconstruction rejects unresolved assembly literal regions; no unverified crypto library emitted or selected.',original_xcodebuild_sha256=original_sha,probe_results=probes,default_launcher_changed=False,default_launcher_sha256=digest('bin/xcodebuild'),full_xcode_build_ready=False,archive_verified=False,signing_ready=False,export_verified=False,complete=False,goal_status='active',next_work=next_work,evidence=evidence,scripts={n:digest(n) for n in scripts})
destination='artifacts/device-identity-progress.json';(root/destination).write_text(json.dumps(record,indent=2)+'\n')
state=read('artifacts/current-work-state.json');state.update(updated_at=record['checked_at'],primary_report=destination,goal_status='active',complete=False,latest_selected_runtime=runtime,latest_xcode_loader_blocker='/usr/lib/libcryptex.dylib',latest_staged_coreml_and_metal_blocker='Required simulator plugin dependency closure',latest_xcode_runtime_failure=record['current_build_failure'],latest_xcode_failure_kind='Cryptex_dependency_crypto_assembly_analysis',latest_implementation_form='Real source IOMainPort forwarding and native-valued Security/Token constants, original Intel DeviceIdentity/Multiverse/bootpolicy/image4 code with native alias. Original version/SDK listing pass strict UTI; full project compilation and signing remain incomplete.',active_build=dict(task='DeviceIdentity-and-Cryptex-original-dependencies',running=False,report=destination),next_work=next_work)
state.setdefault('source_components',{}).update(DeviceIdentity_progress=destination,DeviceIdentity_runtime='artifacts/device-identity-native-stage.json',IOKit_main_entry=builds[0],Security_device_constant=builds[1],CryptoTokenKit_error_domain=builds[2])
state['latest_validation_reports']=list(dict.fromkeys(state.get('latest_validation_reports',[])+list(evidence)+[destination]));(root/'artifacts/current-work-state.json').write_text(json.dumps(state,indent=2)+'\n')
print('Validated native DeviceIdentity/Image4, real source API components and strict original Xcode queries; Cryptex/crypto assembly still blocks project build, full goal active')
