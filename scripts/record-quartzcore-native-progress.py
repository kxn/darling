#!/usr/bin/env python3
"""Verify current native-framework execution/probe evidence and record incomplete work."""

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
from collections import Counter
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

# A historical recorder must not replace the newer directory-service checkpoint.
if json.loads((root / 'artifacts/current-work-state.json').read_text()).get('primary_report') in {'artifacts/libtrace-directory-progress.json', 'artifacts/directory-runtime-progress.json', 'artifacts/directory-services-progress.json', 'artifacts/sysdir-metadata-progress.json', 'artifacts/metadata-kernel-progress.json', 'artifacts/mount-container-progress.json'}:
    print('Preserving the later source logging and directory-service checkpoint')
    raise SystemExit(0)
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
read=lambda p:json.loads((root/p).read_text())
probe_path='artifacts/quartzcore-native-probe.json';probe=read(probe_path)
mode_path='artifacts/ca-display-native-values.json';mode=read(mode_path)
constants_path='artifacts/quartzcore-native-constants.json';constants=read(constants_path)
version=read('artifacts/quartzcore-native-xcode-version.json')
assert probe['exit_status']==255 and '__dyld_get_dlopen_image_header' in probe['diagnostic']
assert not probe['sdk_listing_succeeded']
assert digest(probe['log'])==probe['log_sha256']
assert mode['selected_native_mode_value_api_execution_verified'] and mode['exit_status']==0
assert mode['input_probe_sha256']==digest(probe_path)==version['probe_sha256']
assert digest(mode['log'])==mode['log_sha256']
assert 'DATA_COPY_OK 490\n' in (root/mode['log']).read_text()
assert digest('fixtures/hello/ca-display-native-values.m')==mode['test_source_sha256']
assert digest('artifacts/ca-display-native-values')==mode['test_binary_sha256']
assert digest('artifacts/ca-display-native-analysis.json')==mode['native_metadata_analysis_sha256']
assert digest('artifacts/ca-display-dvt-callers.json')==mode['native_DVT_callers_sha256']
assert mode['source_runtime']==probe['source_runtime']==constants['source_runtime']==version['selected_runtime']
assert version['original_xcode_version_verified'] and version['exit_status']==0
assert digest(version['log'])==version['log_sha256']
for variable,item in probe['source_runtime'].items():assert digest(item['path'])==item['sha256']
assert len(probe['source_runtime'])==6
quartz=probe['native_quartzcore'];assert quartz==mode['native_framework']
assert quartz['restored_original_objc_classes']==145
assert digest(quartz['staged_framework'])==quartz['staged_framework_sha256']
assert digest(quartz['reconstruction_report'])==quartz['reconstruction_report_sha256']
for target,item in quartz['dependency_images'].items():
    assert digest(item['staged_path'])==item['staged_sha256']
    assert digest(item['reconstruction_report'])==item['reconstruction_report_sha256']
assert set(quartz['dependency_images'])=={'symbolication-native','core-symbolication-native'}
assert digest(probe['staged_framework'])==probe['staged_framework_sha256']
assert digest(probe['reconstruction_report'])==probe['reconstruction_report_sha256']
helper=quartz['constants_compatibility'];assert helper['report_sha256']==digest(constants_path)
assert digest(constants['helper'])==constants['helper_sha256']==helper['helper_sha256']
assert constants['legacy_and_original_foundation_type_value_independent_copy_verified']
assert constants['verified_cfstring_count']==143 and constants['verified_extra_identifier_count']==6
assert constants['original_graphics_import_cfstrings']==62
assert digest('config/native-string-constants.json')==constants['config_sha256']
assert digest('fixtures/hello/native-string-constants.c')==constants['test_source_sha256']
assert digest('artifacts/native-string-constants-smoke')==constants['test_binary_sha256']
assert digest('runtime/native-string-constants/cases.h')==constants['generated_header_sha256']
for path,value in constants['logs'].items():assert digest(path)==value
for path,value in constants['native_analyses'].items():assert digest(path)==value
inventory_path='artifacts/quartzcore-native-dependency-inventory.json';inventory=read(inventory_path)
audit_path='artifacts/quartzcore-native-symbol-audit.json';audit=read(audit_path)
chained_path='artifacts/quartzcore-native-chained-import-audit.json';chained=read(chained_path)
assert inventory['runtime_root']=='runtime/sandbox-source/darling-root'
assert not inventory['missing_required_images'] and not inventory['invalid_images']
assert inventory['images_visited']==217
for path,value in audit['image_sha256'].items():assert digest(path)==value
for path,value in chained['image_sha256'].items():assert digest(path)==value
assert not [r for r in audit['unresolved'] if r['binding']=='eager' and not r['weak_import']]
assert not chained['unsupported_images'] and not chained['unresolved_candidates']
sqlite=next(r for r in inventory['images'] if r['image']=='/usr/lib/libsqlite3.0.dylib')
assert '/usr/lib/libsqlite3.dylib' in sqlite['aliases']
source_xpc='runtime/sandbox-source/darling-root/usr/lib/system/libxpc.dylib'
assert audit['image_sha256'][source_xpc]==probe['source_runtime']['LINUXCODE_LIBXPC']['sha256']
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
assert digest(original)==probe['original_xcodebuild_sha256']==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
defaults={}
for relative,value in read('artifacts/libxpc-source.json')['source_configuration']['base_libraries'].items():
    assert digest(relative)==value;defaults[relative]=value
for path in ['artifacts/libsystem-kernel-source.json','artifacts/quarantine-source.json','artifacts/sandbox-source.json']:
    c=read(path)['source_configuration'];assert digest(c['baseline'])==c['baseline_sha256'];defaults[c['baseline']]=c['baseline_sha256']
c=read('artifacts/launchd-source.json')['source_configuration']
assert digest(c['original_launchd'])==c['original_launchd_sha256'];defaults[c['original_launchd']]=c['original_launchd_sha256']
c=read('artifacts/darlingserver-memory-entry.json')
assert digest('runtime/rootfs/usr/bin/darlingserver')==c['default_server_sha256'];defaults['runtime/rootfs/usr/bin/darlingserver']=c['default_server_sha256']
c=read('config/dyld-cache-introspection.json')['legacy_backend']
assert digest('runtime/rootfs/usr/libexec/darling/usr/lib/system/libdyld.dylib')==c['library_sha256']
defaults['runtime/rootfs/usr/libexec/darling/usr/lib/system/libdyld.dylib']=c['library_sha256']
reports=[probe_path,mode_path,constants_path,inventory_path,audit_path,chained_path,
    'artifacts/quartzcore-native-xcode-version.json','artifacts/ca-display-native-analysis.json',
    'artifacts/ca-display-dvt-callers.json','artifacts/cg-hairline-native-analysis.json',
    'artifacts/coreimage-format-native-analysis.json','artifacts/dyld-dlopen-header-source-analysis.json']
bindings=dict(Counter(r['binding']+('_weak' if r['weak_import'] else '_strong') for r in audit['unresolved']))
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),goal_complete=False,
    original_xcodebuild_sha256=digest(original),source_runtime=probe['source_runtime'],
    selected_original_QuartzCore_mode_value_cases=490,selected_native_mode_API_execution_verified=True,
    verified_cfstrings=143,verified_typed_identifiers=6,
    reports={p:digest(p) for p in reports},packaged_defaults_unchanged=defaults,
    dependency_inventory_images=217,classic_binding_slots=audit['binding_slots_checked'],
    remaining_classic_unresolved=bindings,chained_import_records=chained['import_table_records_checked'],
    chained_special_lookup_ordinals_not_audited=chained['special_lookup_ordinals_not_audited'],
    sdk_listing_exit_status=255,sdk_listing_succeeded=False,
    latest_loader_diagnostic='Missing _dyld_get_dlopen_image_header in libSystem/DVTFoundation',
    display_enumeration_verified=False,rendering_or_GPU_implemented=False,
    symbolication_Swift_and_memory_statistics_API_execution_verified=False,
    full_xcode_build_ready=False,signing_ready=False)
(root/'artifacts/quartzcore-native-progress.json').write_text(json.dumps(report,indent=2)+'\n')
state_path=root/'artifacts/current-work-state.json';state=read('artifacts/current-work-state.json')
if state.get('primary_report') == 'artifacts/objc-source-progress.json':
    print('Preserving the later source objc4 checkpoint')
    raise SystemExit(0)
if state.get('primary_report')=='artifacts/uti-native-progress.json':
    print('Preserving the later UTI/runtime-support checkpoint')
    raise SystemExit(0)
state.update(updated_at=datetime.now(timezone.utc).isoformat(),goal_status='active',complete=False,
    latest_staged_coreml_and_metal_blocker='Six-source runtime plus native Foundation/LoggingSupport/QuartzCore/Symbolication/CoreSymbolication now gets original xcodebuild -showsdks past CADisplay and required graphics data bindings. It exits 255 on missing _dyld_get_dlopen_image_header in DVTFoundation/libSystem. Actual original CADisplayMode factory/getter/serialization APIs passed 490 cases; no display enumeration/rendering/GPU or full project build/archive/signing claim.',
    latest_implementation_form='The six source runtime components remain selected with unchanged binaries. This step reconstructs original QuartzCore (145 classes), Symbolication (100) and CoreSymbolication (3) in an isolated experiment alongside native LoggingSupport. External constants helper now has 143 verified CFStrings and six typed identifiers. No CADisplay stub or private object offset implementation was added; external adapters/rebinding remain; no full Darling rebuild. Packaged defaults and original Xcode are unchanged.')
new_work=[
    'Implement _dyld_get_dlopen_image_header at the Darling loader/libdyld source boundary. The modern pinned Apple source returns the actual handle image header, supports RTLD_SELF and RTLD_MAIN_ONLY and returns NULL for invalid handles. The old source lacks both public wrapper and loader function-table entry. Preserve caller identity, real registry/lock and dlopen/dlclose lifetime, RTLD_FIRST, reexport/no-export images and concurrency; do not guess an address/header from an opaque handle or dependency symbol. See artifacts/dyld-dlopen-header-source-analysis.json.',
    'Complete original QuartzCore headless display enumeration/control when required by actual Xcode execution. Only original CADisplayMode value APIs have 490 positive execution cases; CADisplay enumeration, real render/GPU backends, Symbolication memory statistics/Swift APIs and LoggingSupport event decoding remain unverified. Static checks cover 217 images and classic/chained import names, with 889 unresolved strong lazy bindings and other weak/special-lookup gaps; they do not establish full ABI/runtime compatibility.'
]
state['next_work']=new_work+[s for s in state['next_work'] if not s.startswith(('Continue original xcodebuild from CADisplay',
    'Implement _dyld_get_dlopen_image_header at the Darling loader/libdyld source boundary',
    'Complete original QuartzCore headless display enumeration/control'))]
state['last_verification']=list(dict.fromkeys(state['last_verification']+[
    'Original QuartzCore 145-class reconstruction, Symbolication 100-class reconstruction with explicit public Swift coalesced imports, and CoreSymbolication three-class reconstruction staged separately. Original CADisplayMode execution passed 490 factory/dimension/16.16-rate/VRR/hash/equality/16-byte-data-copy cases with actual method-owner checks.',
    '143 CFString and six typed constant values passed both legacy Foundation and native Foundation/all-six-source-component tests. New graphics imports include verified x86_64 double hairline sentinel and SDK-declared signed 32-bit CIFormat values; no graphics/provider operations implemented.',
    'Actual private source-runtime dependency inventory covers 217 images, zero missing required images and 40 missing weak images. Classic audit checks 124198 slots, zero unresolved strong eager imports, 889 strong lazy/174 weak eager/78 weak lazy unresolved. Fifteen chained images have 3676 import-table records and no unresolved candidates, with 12 special lookup records and actual chain traversal still unverified. Physical SQLite symlink aliases are retained rather than misreported absent.',
    'Original Xcode 26.6/17F113 version query passed with the expanded isolated experiment. Original -showsdks now exits 255 on _dyld_get_dlopen_image_header; packaged core binaries and original Xcode hashes remain unchanged. Full SDK listing/project build/archive/signing remain incomplete.'
]))
state['source_components'].update(quartzcore_original_experiment=probe_path,
    ca_display_native_metadata='artifacts/ca-display-native-analysis.json',
    ca_display_native_values=mode_path,quartzcore_native_constants=constants_path,
    quartzcore_native_progress='artifacts/quartzcore-native-progress.json',
    dyld_dlopen_header_source_analysis='artifacts/dyld-dlopen-header-source-analysis.json')
state['latest_validation_reports']=list(dict.fromkeys(state['latest_validation_reports']+reports+['artifacts/quartzcore-native-progress.json']))
state_path.write_text(json.dumps(state,indent=2)+'\n')
print('Verified original mode execution, constants, selected runtime, probes and packaged defaults. Full goal remains active/incomplete.')
