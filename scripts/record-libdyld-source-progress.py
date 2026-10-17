#!/usr/bin/env python3
"""Validate source libdyld execution evidence and advance the incomplete work state."""

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
import hashlib,json,re,subprocess
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
repo=root/'vendor/darling/src/external/dyld'
build=read('artifacts/libdyld-source.json');feature=read('artifacts/dyld-dlopen-header-source.json')
regressions=read('artifacts/libdyld-source-regressions.json')
probe_path='artifacts/quartzcore-native-source-dyld-probe.json';probe=read(probe_path)
mode_path='artifacts/ca-display-native-values-source-dyld.json';mode=read(mode_path)
version_path='artifacts/quartzcore-native-source-dyld-xcode-version.json';version=read(version_path)
selected=feature['selected_runtime']
assert len(selected)==7 and selected==regressions['selected_runtime']==probe['source_runtime']==version['selected_runtime']==mode['source_runtime']
for item in selected.values():assert digest(item['path'])==item['sha256']
assert build['full_libdyld_source_build'] and build['complete_source_files']==28
assert not build['full_loader_source_rebuild'] and not feature['full_loader_source_rebuild']
for path,value in build['source_files'].items():assert digest('vendor/darling/src/external/dyld/'+path)==value
assert build['library_sha256']==selected['LINUXCODE_LIBDYLD']['sha256']
config=read('config/libdyld-source-build.json');assert build['source_configuration']==config
assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==config['source_commit']
for path,value in config['loader_abi_files'].items():assert digest('vendor/darling/src/external/dyld/'+path)==value
for base in ['runtime/rootfs/usr/libexec/darling',build['variant_root']]:
    assert digest(base+'/usr/lib/dyld')==config['packaged_loader_sha256']
assert digest('runtime/rootfs/usr/libexec/darling/usr/lib/system/libdyld.dylib')==config['packaged_libdyld_sha256']
assert digest(build['variant_root']+'/usr/lib/system/libdyld.dylib')==build['library_sha256']
exports=lambda p:set(re.findall(r'^(?:0x[\da-fA-F]+|\[re-export\])\s+(\S+)',subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(root/p)],text=True),re.M))
old=exports('runtime/rootfs/usr/libexec/darling/usr/lib/system/libdyld.dylib');new=exports(selected['LINUXCODE_LIBDYLD']['path'])
assert len(old)==build['original_exports_preserved']==180 and len(new)==build['source_exports']==181
assert not old-new and new-old=={'__dyld_get_dlopen_image_header'}
assert feature['runtime_execution_verified'] and feature['exit_status']==0 and feature['all_real_lifecycle_markers_verified']
assert feature['wrong_loader_abi_rejected_before_execution']
assert digest('fixtures/hello/dyld-dlopen-header.c')==feature['test_source_sha256']
assert digest('artifacts/dyld-dlopen-header')==feature['test_binary_sha256']
assert digest('scripts/test-libdyld-source.py')==feature['test_driver_sha256']
for path,value in feature['tested_fixture_files'].items():assert digest(path)==value
for record in [feature,probe,mode,version]:assert digest(record['log'])==record['log_sha256']
for path,value in regressions['logs'].items():assert digest(path)==value
for name in ['real_snapshot_images_uuids_segments_load_unload_and_rights_verified',
        'real_three_thread_native_exported_tlv_storage_isolation_verified',
        'native_QuartzCore_490_value_cases_verified','original_xcode_version_verified']:assert regressions[name]
assert version['original_xcode_version_verified'] and version['exit_status']==0
assert mode['selected_native_mode_value_api_execution_verified'] and mode['exit_status']==0
assert mode['input_probe_sha256']==version['probe_sha256']==digest(probe_path)
assert probe['exit_status']==255 and '_MAGetPallasEnabled' in probe['diagnostic']
assert not probe['sdk_listing_succeeded'] and 'Symbol not found: __dyld_get_dlopen_image_header' not in probe['diagnostic']
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
assert digest(original)==probe['original_xcodebuild_sha256']==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
patch=root/'artifacts/darling-libdyld-dlopen-header.patch'
patch.write_bytes(subprocess.check_output(['git','-C',str(repo),'diff','--','include/mach-o/dyld_priv.h','src/dyldAPIsInLibSystem.cpp']))
assert patch.stat().st_size>0
subprocess.run(['git','-C',str(repo),'apply','--reverse','--check',str(patch)],check=True)
build.update(runtime_execution_verified=True,
    verified_current_build_inputs={p:digest('vendor/darling/src/external/dyld/'+p) for p in ['CMakeLists.txt','include/mach-o/dyld_priv.h']},
    execution_evidence={p:digest(p) for p in ['artifacts/dyld-dlopen-header-source.json','artifacts/libdyld-source-regressions.json']})
(root/'artifacts/libdyld-source.json').write_text(json.dumps(build,indent=2)+'\n')
reports=['artifacts/libdyld-source.json','artifacts/dyld-dlopen-header-source.json',
    'artifacts/libdyld-source-regressions.json',probe_path,mode_path,version_path,
    'artifacts/dyld-dlopen-header-source-analysis.json','artifacts/darling-libdyld-dlopen-header.patch']
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),source_runtime=selected,
    evidence={p:digest(p) for p in reports},complete_libdyld_source_build=True,
    main_loader_rebuilt=False,pinned_packaged_loader_sha256=config['packaged_loader_sha256'],
    packaged_libdyld_unchanged=True,original_exports_preserved=len(old),exports_added=sorted(new-old),
    actual_handle_lifecycle_and_concurrency_verified=True,regressions_passed=True,
    original_xcodebuild_sha256=digest(original),original_sdk_listing_exit_status=probe['exit_status'],
    current_missing_symbol='_MAGetPallasEnabled',current_probe=probe_path,
    full_xcode_build_ready=False,signing_ready=False)
(root/'artifacts/libdyld-source-progress.json').write_text(json.dumps(report,indent=2)+'\n')
state=read('artifacts/current-work-state.json')
if state.get('primary_report') == 'artifacts/objc-source-progress.json':
    print('Preserving the later source objc4 checkpoint')
    raise SystemExit(0)
if state.get('primary_report')=='artifacts/uti-native-progress.json':
    print('Preserving the later UTI/runtime-support checkpoint')
    raise SystemExit(0)
if state.get('primary_report') in {'artifacts/mobileasset-source-progress.json','artifacts/apple-system-info-native-progress.json','artifacts/security-yield-progress.json'}:
    print('Verified historical source libdyld checkpoint; preserved the newer MobileAsset work state.')
    raise SystemExit(0)
state.update(updated_at=report['checked_at'],goal_status='active',complete=False,
    primary_report='artifacts/libdyld-source-progress.json',
    latest_staged_coreml_and_metal_blocker='Seven selected source runtime components, including complete source libdyld, pass original xcodebuild -version. Original -showsdks exits 255 at MAGetPallasEnabled in MobileAsset. The previous _dyld_get_dlopen_image_header blocker is resolved in source; SDK listing/build/archive/signing remain incomplete.',
    latest_implementation_form='Seven source components selected privately. Complete libdyld (28 sources) retains all 180 old exports and adds the actual handle-header SPI, using the pinned packaged dyld2 main loader ABI. Main loader is not rebuilt. External adapters, native-framework reconstruction and constants helpers remain; original Xcode and packaged libdyld are unchanged.')
state['next_work']=[
    'Implement actual MobileAsset Pallas client protocol required by MAGetPallasEnabled. Native Intel code returns a signed 64-bit service response code and writes a separate boolean output; it sends messageAction 32 over XPC, not a simple preference flag. Inspect native manager/service schema and DVT callers before implementation. Do not return fabricated success or conflate the return code with enabled state.'
]+[s for s in state['next_work'] if not s.startswith(('Implement _dyld_get_dlopen_image_header','Implement actual MobileAsset Pallas'))]
state['last_verification'].append('Complete source libdyld: 180 original exports retained; actual no-export/reexport/multiple-reference/duplicate-module/RTLD_SELF/main/invalid/error-state lifecycle cases and 512 concurrent load-query-close cycles passed. Wrong main-loader ABI rejected. Seven-component snapshot/TLV/490 QuartzCore value cases and original Xcode version passed; SDK listing now reaches missing MAGetPallasEnabled.')
state['source_components'].update(libdyld='artifacts/libdyld-source.json',
    libdyld_execution='artifacts/dyld-dlopen-header-source.json',libdyld_integration='artifacts/libdyld-source-progress.json',
    source_dyld_xcode_probe=probe_path)
state['latest_validation_reports']=list(dict.fromkeys(state['latest_validation_reports']+reports+['artifacts/libdyld-source-progress.json']))
state['known_scope_limits']=[s for s in state['known_scope_limits'] if not s.startswith(('Source server not installed/default; original generic CPU subtype','XPC shared-memory object and serialization, launchd control statistics'))]
state['known_scope_limits']+=['Source components are selected explicitly; the default packaged environment remains a separate baseline.',
    'Full source libdyld is coupled to the pinned dyld2 C++ loader ABI; main-loader rebuild, other loader revisions and dyld3 remain unsupported by this path.']
(root/'artifacts/current-work-state.json').write_text(json.dumps(state,indent=2)+'\n')
print('Verified seven-component source libdyld progress; genuine -showsdks is now blocked by MAGetPallasEnabled. Full goal remains active.')
