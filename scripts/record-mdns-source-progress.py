#!/usr/bin/env python3
"""Verify original package dependencies, source XPC and Security value classes."""

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
from pathlib import Path as _cloud_Path
import json as _cloud_json
_cloud_state = _cloud_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _cloud_state.exists() and _cloud_json.loads(_cloud_state.read_text()).get('primary_report') in {'artifacts/security-cloud-rpc-progress.json','artifacts/security-current-item-progress.json','artifacts/sandbox-check-progress.json','artifacts/expected-sandbox-runtime-progress.json','artifacts/coreutils-quarantine-progress.json'}:
    print('Preserving newer Security RPC source checkpoint; historical recorder skipped')
    raise SystemExit(0)
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,re,runpy,struct,subprocess
root=Path(__file__).resolve().parent.parent
read=lambda name:json.loads((root/name).read_text())
digest=lambda name:hashlib.sha256((root/name).read_bytes()).hexdigest()
p=runpy.run_path(str(root/'scripts/mdns-native-profile.py'))['profile']()
stage=p['native_mdns'];runtime=p['xpc_collections_runtime'];source=p['source_xpc_collections']
assert source['full_libxpc_source_build'] and source['complete_source_files']==39 and source['source_exports']==640
assert len(stage['images'])==12
for item in p['source_runtime'].values():assert digest(item['path'])==item['sha256']
for image in stage['images']:
    data=read(image['reconstruction']);assert not data['redirected_imports'] and not data['backend_call_overrides']
    assert digest(image['source'])==digest(image['library'])==data['staged_image_sha256']
    assert digest(image['reconstruction'])==image['reconstruction_sha256']
    name=data['target'];entry=read('config/cache-image-pins.json')[name]
    assert digest('runtime/fullsystem-libraries/'+entry['path'].lstrip('/'))==entry['sha256']==data['original_image_sha256']
mobile=stage['mobile_device'];assert mobile['install_location']=='/Library/Apple' and not mobile['kernel_extensions_loaded'] and not mobile['package_scripts_executed']
assert read('runtime/xcode-mobile-device-extraction.json')['checksum_verified']
assert read(mobile['package_info']+'.json')['xar_content_checksums_verified']
assert 'system-volume-group-install-location="/Library/Apple/"' in (root/mobile['package_info']).read_text()
for name,target in stage['overlay_links'].items():assert os.readlink(root/name)==target
for name in read('artifacts/xcode-system-resources-stage.json')['prefix_links']:assert not (root/name).is_symlink() and not (root/name).exists()
assert not list((root/'runtime/state/prefix/Library/Apple').iterdir())
paths={'arrays':'artifacts/xpc-array-empty-test.json','mdns':'artifacts/mdns-native-test.json','values':'artifacts/security-out-of-band-values-test.json','version':'artifacts/xcode-service-runtime-mdns-base-version.json','sdk':'artifacts/xcode-service-runtime-mdns-base-showsdks.json','build':'artifacts/xcode-service-runtime-mdns-build.json'}
results={name:read(path) for name,path in paths.items()}
for name,data in results.items():
    assert data['source_runtime']==p['source_runtime'],name
    if 'log' in data:assert digest(data['log'])==data['log_sha256']
    if 'source' in data:assert digest(data['source'])==data['source_sha256']
    if 'binary' in data:assert digest(data['binary'])==data['binary_sha256']
    for check in data.get('checks',[]):assert digest(check['log'])==check['log_sha256']
arrays=results['arrays'];assert arrays['runtime_execution_verified'] and len(arrays['checks'])==2
assert arrays['checks'][0]['exit_status']!=0 and arrays['checks'][1]['exit_status']==0
assert 'checks=1041' in (root/arrays['checks'][1]['log']).read_text()
assert arrays['checks'][0]['source_runtime']==runtime['previous_source_runtime']
mdns=results['mdns'];assert mdns['selected_TLV_execution_verified'] and mdns['remote_class_registration_verified'] and not mdns['eager_library_bind_verified']
assert [c['exit_status'] for c in mdns['checks']]==[0,2,0]
assert 'checks=307 mode=lazy' in (root/mdns['checks'][0]['log']).read_text()
assert '__dyld_dlsym_blocked' in (root/mdns['checks'][1]['log']).read_text()
assert 'checks=56 classes=14' in (root/mdns['checks'][2]['log']).read_text()
values=results['values'];assert values['exit_status']==0 and values['value_class_execution_verified'] and not values['cloud_keychain_RPC_execution_verified']
assert not values['strict_declared_field_type_enforcement_verified']
assert 'checks=102 classes=4' in (root/values['log']).read_text()
assert 'SECURE_ARCHIVE_NUMERIC_PRIMITIVE_OBSERVED accepted=1 error=0' in (root/values['log']).read_text()
value_build=stage['security_value_classes']['build'];assert len(value_build['exports'])==8
for name,sha in value_build['sources'].items():assert digest(name)==sha
for name in ['version','sdk','build']:
    data=results[name];assert data['UTI_preflight_verified']
    assert digest(data['script'])==data['script_sha256']
    assert '/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild "$@"' in (root/data['script']).read_text()
    for job in data['jobs']:assert digest(job['path'])==job['sha256']
    assert data['native_mdns']==stage
assert results['version']['exit_status']==0 and results['sdk']['exit_status']==0
assert not results['version']['use_original_developer_overlay'] and not results['sdk']['use_original_developer_overlay']
assert 'Xcode 26.6\nBuild version 17F113' in (root/results['version']['log']).read_text()
sdk_text=(root/results['sdk']['log']).read_text()
for marker in ['DriverKit SDKs:','iOS SDKs:','macOS SDKs:','tvOS SDKs:','visionOS SDKs:','watchOS SDKs:','SERVICE_RUNTIME_XCODE_STATUS 0']:assert marker in sdk_text
lsd_snapshot=sdk_text.split('+ launchctl list com.apple.lsd\n',1)[1].split('+ exit',1)[0]
lsd_last_exit=int(re.search(r'"LastExitStatus" = (\d+);',lsd_snapshot).group(1))
lsd_pid=re.search(r'"PID" = (\d+);',lsd_snapshot)
lsd_snapshot_record={'last_exit_status':lsd_last_exit,'pid':int(lsd_pid.group(1)) if lsd_pid else None,'long_term_service_stability_verified':False}
build=results['build'];build_text=(root/build['log']).read_text()
assert build['use_original_developer_overlay'] and build['exit_status']==255
assert 'Symbol not found: _SecItemUnsetCurrentItemsAcrossAllDevices' in build_text and 'SERVICE_RUNTIME_XCODE_STATUS 255' in build_text
assert '** BUILD SUCCEEDED **' not in build_text
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
assert digest(original)==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')==build['original_xcodebuild_sha256']
layout=read('artifacts/remote-xpc-page-layout-test.json');assert layout['no_vm_segment_overlap'] and layout['original_ctf_bytes_preserved']==824
assert digest(layout['corrected'])==layout['corrected_sha256']
assert digest(layout['overlap_control'])==layout['overlap_control_sha256']
assert 'segment __CTF vm overlaps segment __DATA' in (root/'logs/mdns-remote-xpc-overlap-failure.log').read_text()
assert stage['security_identifier']['export_changes']['original_instructions_and_other_bytes_preserved']
assert stage['security_value_classes']['export_changes']['original_instructions_and_other_bytes_preserved']
patches=['artifacts/darling-xpc-collections-source.patch','artifacts/darling-security-out-of-band-values-source.patch']
for repo,patch in zip(['vendor/darling/src/external/libxpc','vendor/darling/src/external/security'],patches):subprocess.run(['git','apply','--reverse','--check',str(root/patch)],cwd=root/repo,check=True)
evidence=list(paths.values())+patches+['artifacts/mdns-native-stage.json','artifacts/xpc-collections-source-build.json','artifacts/xpc-collections-runtime-stage.json','artifacts/security-out-of-band-values-build.json','config/security-out-of-band-values.json','artifacts/mdns-next-runtime-analysis.json','artifacts/remote-xpc-page-layout-test.json','artifacts/mdns-remote-xpc-overlap-failure.json','logs/mdns-remote-xpc-overlap-failure.log','artifacts/mdns-dependency-inventory.json','artifacts/storage-kit-dependency-candidates.json','artifacts/disk-images2-public-import-recovery.json','runtime/xcode-mobile-device-extraction.json','runtime/xcode-mobile-device-PackageInfo.xml','runtime/xcode-mobile-device-PackageInfo.xml.json']
for data in results.values():
    if 'log' in data:evidence.append(data['log'])
    evidence.extend(check['log'] for check in data.get('checks',[]))
    evidence.extend(data.get('service_logs',{}))
evidence.extend(image['reconstruction'] for image in stage['images'])
scripts=['scripts/record-mdns-source-progress.py','scripts/rebuild-c-cache-image.py','scripts/build-libxpc-source.py','scripts/stage-xpc-collections-runtime.py','scripts/stage-mdns-native.py','scripts/mdns-native-profile.py','scripts/probe-xcode-service-runtime.py','scripts/runtime-ns.sh','scripts/test-mdns-native.py','scripts/test-xpc-array-empty.py','scripts/build-security-out-of-band-values.py','scripts/test-security-out-of-band-values.py','scripts/extract-xar-member.py']
record={'checked_at':datetime.now(timezone.utc).isoformat(),'previous_report':'artifacts/log-pack-progress.json','previous_goal_turn_classification':'progress','current_goal_turn_classification':'progress','source_runtime':p['source_runtime'],'source_xpc_collections':source,'native_images':stage['images'],'selected_mdns_execution_verified':True,'remote_class_registration_verified':True,'source_array_execution_verified':True,'Security_value_class_execution_verified':True,'full_library_eager_bind_verified':False,'baseline_original_version_exit':0,'baseline_original_sdk_exit':0,'lsd_post_sdk_snapshot':lsd_snapshot_record,'original_project_with_system_resources_exit':255,'original_project_blocker':'_SecItemUnsetCurrentItemsAcrossAllDevices from ProtectedCloudStorage requires genuine Security client RPC/protocol/backend integration','temporary_package_mounts_verified_by_original_loader':True,'package_scripts_or_kernel_extensions_executed':False,'shared_framework_prefix_published':False,'default_launcher_switched':False,'full_xcode_build_ready':False,'signing_ready':False,'goal_status':'active','complete':False,'original_xcodebuild_sha256':digest(original),'implementation_form':'Twelve original cache images restored with classic bindings and typed metadata; original XcodeSystemResources and MobileDevice package payloads mounted only in the guest server namespace. Explicit RemoteXPC shared-page coalescing retains all 824 CTF bytes and original addresses/protections. xpc_array_create_empty is in Darling source and the complete 39-file libxpc is rebuilt into a matching private 7-component directory variant. Four unchanged Apple NSSecureCoding value-class implementations are integrated into Darling Security source and compiled separately; named reexports preserve the existing Security code. No cloud RPC/keychain policy success is simulated.','evidence':{name:digest(name) for name in dict.fromkeys(evidence)},'scripts':{name:digest(name) for name in scripts},'configuration_sha256':digest('config/cache-image-pins.json'),'limits':['The expanded original package profile still cannot load the actual project: Security cloud/keychain RPC exports are missing. No project build, archive, signing or export succeeded. Baseline version/SDK success excludes the optional original Developer/Apple package mounts and is a regression check, not proof of the extended profile.','The selected original mdns TLV code and actual RemoteXPC/RSD Objective-C class registration execute. Network discovery, remote channels, packet filtering, disk operations, StorageKit/DiskImages2 Swift behavior and the complete native dependency closure are not proven by these checks.','RTLD_NOW still fails on __dyld_dlsym_blocked in the previously staged LoggingSupport dependency. No missing function was converted to success or a dummy value to satisfy this check.','The four source query/result classes are data values only. Full Security was not rebuilt, and source client RPCs, securityd protocol updates, cloud services, keychain-option enforcement and certificate trust evaluation are unverified.','Original Foundation accepted an inline NSNumber for a declared NSString field in the retained probe. The class test proves archive roundtrip and rejects an unapproved custom class before initWithCoder; strict declared-field type enforcement is explicitly not claimed.','CTF bytes and addresses are retained under the merged __DATA segment, but separate __CTF segment-name discovery/DTrace tooling compatibility is unverified.','Package archive checksums are verified; installer CMS trust, receipts, postinstall/DDI updates and first-launch completion remain unverified. Only an empty task-prefix Library/Apple mount-target directory persists; framework contents are not published.','Latest SDK snapshot records a live lsd PID with last status 0; earlier runs exited 132. This snapshot does not prove durable notification service support. The native distnoted sandbox-reference/API gap and earlier CF timing, filesystem metadata, sandbox/XPC authorization, graphics and signing/trust limitations remain.']}
destination='artifacts/mdns-source-progress.json';pending=root/(destination+'.pending');pending.write_text(json.dumps(record,indent=2)+'\n');pending.replace(root/destination)
state=read('artifacts/current-work-state.json');state.update(updated_at=record['checked_at'],primary_report=destination,goal_status='active',complete=False,latest_selected_runtime=p['source_runtime'],latest_implementation_form=record['implementation_form'],latest_xcode_loader_blocker=record['original_project_blocker'],latest_xcode_runtime_failure='Expanded original system-resource profile cannot load missing Security RPC export; baseline SDK listing succeeds with lsd PID at snapshot; durable notification support unverified',latest_xcode_failure_kind='Security_client_RPC_and_notification_service',latest_staged_coreml_and_metal_blocker=record['original_project_blocker'],latest_sdk_listing_succeeded=True,active_build={'task':'original-package-dependencies-source-XPC-and-Security-values','running':False,'report':destination})
next_work=read('artifacts/mdns-next-runtime-analysis.json')['next_work'];old=[item for item in state['next_work'] if not item.startswith(('Restore the required original libmdns','After initialization succeeds, continue actual preserved project','Implement source sandbox reference lifetime/audit identity'))]
state['next_work']=list(dict.fromkeys(next_work+old))
state['last_verification'].append('Complete source libxpc rebuilt from 39 files, 640 exports, with real empty-array construction: old-runtime missing-symbol control and 1041 source mutation/ownership/growth/apply checks pass. Original mdns TLV executes 307 checks; original RemoteXPC/RSD register 14 real classes with 56 checks. Four unchanged Apple Security query/result classes match native sizes/15 ivar offsets and pass 102 archive/ownership/custom-class-rejection checks; numeric primitive acceptance is recorded separately. Twelve original images plus two Xcode package payloads are staged in private mount namespaces. Baseline version/SDK remain exit 0; extended original project exits 255 on missing Security client RPC. Full goal remains incomplete.')
state['latest_validation_reports']=list(dict.fromkeys(state['latest_validation_reports']+evidence+[destination]))
state['source_components'].update(libxpc='artifacts/xpc-collections-source-build.json',xpc_collections_runtime='artifacts/xpc-collections-runtime-stage.json',xpc_collections_execution='artifacts/xpc-array-empty-test.json',native_mdns='artifacts/mdns-native-stage.json',native_mdns_execution='artifacts/mdns-native-test.json',security_out_of_band_values='artifacts/security-out-of-band-values-build.json',security_out_of_band_values_execution='artifacts/security-out-of-band-values-test.json',mdns_source_progress=destination)
pending=root/'artifacts/current-work-state.json.pending';pending.write_text(json.dumps(state,indent=2)+'\n');pending.replace(root/'artifacts/current-work-state.json');print('Recorded original dependency restoration, real source XPC/value classes and remaining Security RPC failure; goal remains active')
