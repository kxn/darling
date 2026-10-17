#!/usr/bin/env python3
"""Record paired native enumeration and the observed Foundation metadata failure."""

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
# A historical recorder must not replace the current dependency/source checkpoint.
from pathlib import Path as _mdns_Path
import json as _mdns_json
_mdns_state = _mdns_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _mdns_state.exists() and _mdns_json.loads(_mdns_state.read_text()).get('primary_report') in {'artifacts/mdns-source-progress.json','artifacts/security-cloud-rpc-progress.json','artifacts/security-current-item-progress.json','artifacts/sandbox-check-progress.json','artifacts/expected-sandbox-runtime-progress.json','artifacts/coreutils-quarantine-progress.json'}:
    print('Preserving newer mdns/source checkpoint; historical recorder skipped')
    raise SystemExit(0)
# Preserve the newer source log-pack/FSEvents checkpoint when replaying an old recorder.
import json as _pack_json
from pathlib import Path as _PackPath
_pack_state = _PackPath(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _pack_state.exists() and _pack_json.loads(_pack_state.read_text()).get('primary_report') == 'artifacts/log-pack-progress.json':
    print('Preserving newer source log-pack/FSEvents checkpoint')
    raise SystemExit(0)
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
root=Path(__file__).resolve().parent.parent
if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') == 'artifacts/foundation-coherent-progress.json':
    print('Preserving the newer source selector/coherent Foundation/SDK checkpoint')
    raise SystemExit(0)

if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') == 'artifacts/fsevents-flush-progress.json':
    print('Preserving the newer source FSEvents flush checkpoint')
    raise SystemExit(0)

if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') == 'artifacts/combine-fsevents-progress.json':
    print('Preserving the newer original Combine/source FSEvents checkpoint')
    raise SystemExit(0)

if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') == 'artifacts/imageio-native-progress.json':
    print('Preserving the newer original ImageIO/source-ABI checkpoint')
    raise SystemExit(0)

if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') == 'artifacts/mobilegestalt-progress.json':
    print('Preserving the newer MobileGestalt/source-dyld checkpoint')
    raise SystemExit(0)

if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') in {'artifacts/layer-log-progress.json','artifacts/log-hooks-progress.json'}:
    print('Preserving the newer source layer/log checkpoint')
    raise SystemExit(0)

read=lambda p:json.loads((root/p).read_text())
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
if read('artifacts/current-work-state.json').get('primary_report') in {'artifacts/metadata-kernel-progress.json', 'artifacts/mount-container-progress.json'}:
    print('Newer source metadata checkpoint is active; historical recorder will not overwrite it')
    raise SystemExit(0)
stage=read('artifacts/sysdir-native-export-stage.json')
test=read('artifacts/sysdir-native-export-execution.json')
analysis=read('artifacts/sysdir-native-analysis.json')
assert test['stage']==stage and test['exit_status']==0 and test['runtime_execution_verified']
for key in ['base','library','helper','original_provider','source']:assert digest(stage[key])==stage[key+'_sha256']
assert stage['base_sha256']==read('artifacts/sandbox-container-source-stage.json')['library_sha256']
assert stage['export_changes']['added_names']==['_sysdir_start_search_path_enumeration','_sysdir_start_search_path_enumeration_private','_sysdir_get_next_search_path_enumeration']
assert stage['export_changes']['original_instructions_and_other_bytes_preserved'] and not stage['export_changes']['provider_entire_namespace_reexported']
assert digest(test['log'])==test['log_sha256']
assert digest('fixtures/hello/sysdir-native-export.c')==test['source_sha256']
assert digest('artifacts/sysdir-native-export')==test['binary_sha256']
assert 'NATIVE_SYSDIR_THREE_PAIRED_ENTRIES_STATE_PATH_ORDER_TERMINATION_BOUNDS_AND_PRIVATE_MASKS_OK 2210 1939 168' in test['diagnostic']
assert analysis['state_width']==32 and analysis['common_starter_body'] and analysis['public_excluded_domain_bits']==0x1ff0
assert digest(analysis['log'])==analysis['log_sha256']
prefix='artifacts/uniform-type-identifiers-native-xcode-sysdir-sandbox-container-nounlink-typed-malloc-simple-log-datavault-user-local-dir-source-libtrace-source-objc-support-'
probe,version=read(prefix+'showsdks.json'),read(prefix+'version.json')
integration=read('artifacts/sysdir-native-integration.json')
directory_path='artifacts/native-dirhelper-sysdir-sandbox-container-nounlink-typed-malloc-source-simple-log-probe.json'
directory=read(directory_path)
lsd_path='artifacts/native-lsd-sysdir-paired-dirhelper-sandbox-container-datavault-user-local-dir-source-libtrace-probe.json'
lsd=read(lsd_path)
for item in [probe,version,integration,directory,lsd]:
    assert item['native_sysdir']==stage
    if 'log' in item:assert digest(item['log'])==item['log_sha256']
    for path,sha in item.get('logs',{}).items():assert digest(path)==sha
assert version['exit_status']==0 and 'Xcode 26.6\nBuild version 17F113' in version['diagnostic']
assert probe['exit_status']==255 and 'Symbol not found: _OBJC_CLASS_$_CALayerContext' in probe['diagnostic']
assert integration['runtime_execution_verified'] and directory['runtime_execution_verified']
assert directory['original_binary_sha256']==directory['staged_binary_sha256']==digest('runtime/native-dirhelper/dirhelper')
assert lsd['original_binary_sha256']==lsd['staged_binary_sha256']==digest('runtime/native-lsd/lsd')
assert lsd['exit_status']==1 and not lsd['UTI_functional_execution_verified']
assert len(lsd['selected_job']['MachServices'])==13 and lsd['paired_dirhelper_job']['MachServices']=={'com.apple.bsd.dirhelper':True}
assert 'Symbol not found: _container_query_create' in lsd['daemon_diagnostic']
assert 'Symbol not found: _sysdir_' not in lsd['daemon_diagnostic']
assert '#LSDatabaseBuilder register remote placeholders' in lsd['daemon_diagnostic']
assert 'Error -50 registering path /System/Library/CoreServices/CoreTypes.bundle' in lsd['daemon_diagnostic']
metadata=read('artifacts/coretypes-getattr-request-analysis.json')
assert metadata['original_Foundation_metadata_requests_observed'] and metadata['source_mask_rejection_explains_EINVAL']
assert not metadata['backend_modified'] and not metadata['metadata_fixed']
assert len(metadata['requests'])==4 and all(item['rejected_by_current_supported_mask_checks'] for item in metadata['requests'])
for path,sha in metadata['evidence'].items():assert digest(path)==sha
build=read('artifacts/coretypes-resource-values-build.json')
for result in [read('artifacts/coretypes-resource-values.json'),read('artifacts/coretypes-resource-values-debug.json')]:
    assert result['exit_status']==1 and not result['Foundation_URL_and_enumeration_verified']
    assert digest(result['log'])==result['log_sha256']
    assert result['source_sha256']==build['source_sha256']==digest(build['source'])
    assert result['binary_sha256']==build['binary_sha256']==digest(build['binary'])
    assert 'CORETYPES_METADATA_RESULT directory=0 attributes=1 enumeration=0 errors=1' in (root/result['log']).read_text()
selected=probe['source_runtime']
assert selected==version['source_runtime']==test['source_runtime']==integration['selected_runtime']==directory['source_runtime']==lsd['source_runtime']
assert selected==read('artifacts/directory-services-progress.json')['selected_runtime']
for item in selected.values():assert digest(item['path'])==item['sha256']
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
assert digest(original)==probe['original_xcodebuild_sha256']==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
paths=['artifacts/sysdir-native-export-stage.json','artifacts/sysdir-native-export-execution.json','artifacts/sysdir-native-analysis.json',
    prefix+'showsdks.json',prefix+'version.json','artifacts/sysdir-native-integration.json',directory_path,lsd_path,
    'artifacts/coretypes-resource-values-build.json','artifacts/coretypes-resource-values.json','artifacts/coretypes-resource-values-debug.json',
    'artifacts/coretypes-getattr-request-analysis.json']
scripts=['sysdir-native-loader.c','stage-sysdir-native-export.py','test-sysdir-native-export.py','analyze-sysdir-native.py',
    'build-coretypes-resource-fixture.py','probe-coretypes-resource-values.py','analyze-coretypes-getattr-requests.py',
    'probe-uniform-type-identifiers-native.py','probe-native-dirhelper.py','probe-native-lsd.py','test-objc-source-integration.py','record-sysdir-metadata-progress.py']
destination='artifacts/sysdir-metadata-progress.json'
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),evidence={p:digest(p) for p in paths},
    scripts={'scripts/'+p:digest('scripts/'+p) for p in scripts},selected_runtime=selected,
    three_original_enumeration_entries_paired=True,enumeration_cases=2210,returned_paths_compared=1939,private_public_state_differences=168,
    original_dirhelper_start_and_existing_directory_initialization_verified=True,
    original_lsd_reaches_remote_placeholder_registration=True,original_lsd_start_succeeded=False,
    actual_Foundation_getattrlist_requests_observed=True,underlying_metadata_support_fixed=False,
    original_xcode_version_verified=True,sdk_listing_verified=False,full_UTI_client_verified=False,
    full_xcode_build_ready=False,signing_ready=False,
    implementation_form='Three typed deferred sysdir entries in one private provider execute the same unchanged original Intel directory helper. Public/private starters and get-next stay paired; actual paths/state/order are retained. Live debugger observation captures real Foundation metadata requests without modifying kernel source or installed binaries. The kernel implementation, original Xcode and seven previously selected source runtime binaries are unchanged.',
    limits=['The native path matrix proves enumeration values and ABI, not that each directory exists or that applications were registered.',
        'Original lsd now reaches remote placeholder registration but cannot load container_query_create. A running database service and complete UTI operations are still unverified.',
        'Four genuine Foundation getattrlistat requests are rejected by the current source supported-mask checks. A traditional attributes dictionary is returned, but NSURL directory metadata and directory enumeration still fail EINVAL. No metadata success was fabricated.',
        'Kernel metadata work must implement real stat-backed attributes, returned masks, extended-common interpretation, Darwin packing/reference offsets and bounded buffer semantics. Existing protection/ownership limitations remain.',
        'Latest Xcode version and 54-image loader/policy integration pass; SDK listing still lacks CALayerContext. Complete build/archive/signing/export remain incomplete.'])
(root/destination).write_text(json.dumps(record,indent=2)+'\n')
state=read('artifacts/current-work-state.json')
state.update(updated_at=record['checked_at'],goal_status='active',complete=False,primary_report=destination,
    active_build=dict(task='native-sysdir-and-observed-metadata-requests',running=False,report=destination),
    latest_implementation_form=record['implementation_form'],
    latest_staged_coreml_and_metal_blocker='Paired original sysdir entries pass 2210 cases/1939 paths and move lsd past private enumeration to missing container_query_create. Actual Foundation getattrlistat requests for CoreTypes exceed the old kernel supported masks and fail EINVAL; CoreTypes catalog and full UTI client are still unavailable. Genuine version and 54-image loader/policy integration pass; SDK listing still lacks CALayerContext. Full build/archive/signing/export remain incomplete.')
state['next_work']=list(dict.fromkeys([
    'Implement real metadata in the shared source kernel getattrlist_generic.c path. Live Foundation requests are captured in artifacts/coretypes-getattr-request-analysis.json: common d01f9e0d/d01fde0d with dir 5, file 1, extended-common 240 and options 25; another fullpath request uses common 8800000a/options29. Preserve actual stat-backed values, returned attribute masks, FSOPT_ATTR_CMN_EXTENDED, packing/reference offsets, output size limits and unsupported errors. Recheck genuine URL/NSFileManager and original LaunchServices registration; do not hard-code CoreTypes or advertise unavailable fields.',
    'Restore the real container_query_create and subsequent required ContainerManager ABI used while lsd registers remote placeholders. Reuse original provider/source when possible; preserve actual query/error/lifetime semantics and do not fabricate container records or successful service responses.',
]+[s for s in state['next_work'] if not s.startswith(('Restore the real private sysdir enumeration required by lsd.','Resolve actual file-metadata errors while original LaunchServices registers CoreTypes.bundle:'))]))
state['last_verification']=list(dict.fromkeys(state['last_verification']+[
    'Paired native public/private sysdir entries pass 2210 matrices, 1939 returned paths and 168 distinct private/public states. Original lsd advances to remote-placeholder registration and missing container_query_create. A real Foundation metadata reproducer and live kernel breakpoint capture four requests rejected by existing supported-mask checks; this diagnoses EINVAL without changing the kernel. Genuine version and 54-image snapshot/128 policies pass. Full UTI/database/build/signing remain incomplete.']))
state['latest_validation_reports']=list(dict.fromkeys(state['latest_validation_reports']+paths+[destination]))
state.setdefault('source_components',{}).update(native_sysdir='artifacts/sysdir-native-export-stage.json',CoreTypes_metadata_diagnostic='artifacts/coretypes-getattr-request-analysis.json',sysdir_metadata_progress=destination)
(root/'artifacts/current-work-state.json').write_text(json.dumps(state,indent=2)+'\n')
print('Recorded paired enumeration progress and observed metadata blocker; full Xcode goal remains active')
