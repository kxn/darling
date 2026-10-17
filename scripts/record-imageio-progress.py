#!/usr/bin/env python3
"""Check actual native ImageIO execution and publish the next genuine Xcode blocker."""

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
import hashlib,json,runpy,subprocess
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

read=lambda n:json.loads((root/n).read_text());digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
p=runpy.run_path(str(root/'scripts/imageio-native-profile.py'))['profile']();selected=p['source_runtime']
for v in selected.values():assert digest(v['path'])==v['sha256']
keys=['imageio_native','imageio_cg_constants','simd_matrix','imageio_legacy_key','runnable_archs','source_libdyld','mobilegestalt_native']
paths={'global':'artifacts/imageio-native-global-probe.json','properties_failure':'artifacts/imageio-native-properties-probe.json','allocators':'artifacts/imageio-allocators-test.json','version':'artifacts/imageio-native-xcode-version.json','showsdks':'artifacts/imageio-native-xcode-showsdks.json','lsd':'artifacts/native-lsd-imageio-native-probe.json'}
results={k:read(n) for k,n in paths.items()}
for name,r in results.items():
 assert r['source_runtime']==selected
 for key in keys:assert r[key]==p[key]
 if 'log' in r:assert digest(r['log'])==r['log_sha256']
 for n,sha in r.get('logs',{}).items():assert digest(n)==sha
 if name not in ['properties_failure','showsdks']:assert r['exit_status']==0
assert len(p['imageio_native']['entries'])==11
pins=read('config/cache-image-pins.json')
for e in p['imageio_native']['entries']:
 r=read(e['reconstruction']);assert not r['backend_call_overrides'];assert set(r['redirected_imports'])==set(pins[e['target']].get('import_providers',{}))
 for key in ['original','source','library','reconstruction']:assert digest(e[key])==e[key+'_sha256']
assert p['imageio_native']['entries'][0]['exports']==6522
imageio=read(p['imageio_native']['entries'][0]['reconstruction']);assert imageio['code_analysis']['function_entries']==9814 and len(imageio['code_analysis']['tail_tables'])==201
assert p['imageio_cg_constants']['constant_count']==34 and p['simd_matrix']['source_bytes_equal_original']
for key in ['imageio_cg_constants','imageio_legacy_key','simd_matrix']:
 assert p[key]['export_changes']['original_instructions_and_other_bytes_preserved']
 assert not p[key]['export_changes']['provider_entire_namespace_reexported']
for mode in ['global','properties_failure']:
 r=results[mode];assert r['source_sha256']==digest('fixtures/hello/imageio-native.m') and r['binary_sha256']==digest('artifacts/imageio-native')
r=results['global'];assert r['runtime_execution_verified'] and r['source_global_properties_verified'] and not r['image_parsing_and_metadata_verified']
text=(root/r['log']).read_text();assert 'mode=global cases=6' in text and 'NATIVE_IMAGEIO_CG_CONSTANTS_REAL_CFSTRING_VALUES_OK 34' in text and 'NATIVE_IMAGEIO_SOURCE_SIMD_MATRIX_LAYOUT_OK' in text
for fixture in read('artifacts/imageio-input-fixtures.json'):assert text.count('FileSize = '+str(fixture['bytes'])+';')==2
assert text.count('LoopCount = 4;')==2
failure=results['properties_failure'];assert failure['exit_status']==1 and not failure['runtime_execution_verified']
assert 'Symbol not found: _CGImageProviderCreate' in (root/failure['log']).read_text()
a=results['allocators'];assert a['runtime_execution_verified'] and a['source_sha256']==digest('fixtures/hello/imageio-allocators.cpp') and a['binary_sha256']==digest('artifacts/imageio-allocators')
text=(root/a['log']).read_text();assert 'array=0 allocations=448' in text and 'array=1 allocations=448' in text
lsd=results['lsd'];assert lsd['UTI_functional_execution_verified'] and not lsd['frozen_trace_comparison'];assert 'NATIVE_UTI_TYPED_TAG_CONFORMANCE_AND_URL_EXTENSION_OK' in lsd['diagnostic']
assert 'Symbol not found:' not in lsd['daemon_diagnostic'] and 'Error -43 registering path /System/Library/CoreServices/CoreTypes.bundle' not in lsd['daemon_diagnostic']
for arg in p['command']:
 if arg.startswith(('DYLD_LIBRARY_PATH=','DYLD_FRAMEWORK_PATH=')):
  k,v=arg.split('=',1);assert lsd['selected_job']['EnvironmentVariables'][k]==v
assert 'Xcode 26.6\nBuild version 17F113' in (root/results['version']['log']).read_text()
blocker='_$s7Combine4JustV14setFailureType2tos6ResultOAAE9PublisherVyxqd___Gqd__m_ts5ErrorRd__lF'
assert results['showsdks']['exit_status']==255 and 'Symbol not found: '+blocker in (root/results['showsdks']['log']).read_text()
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild';assert digest(original)==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
for key in ['version','showsdks']:assert results[key]['original_xcodebuild_sha256']==digest(original)
for item in read('artifacts/imageio-input-fixtures.json'):assert digest(item['path'])==item['sha256']
patches=[]
for repo,tracked,added,out in [
 ('vendor/darling',['src/libm/CMakeLists.txt','src/frameworks/ImageIO/CMakeLists.txt','src/frameworks/ImageIO/src/CGImageDestination.m'],['src/libm/Source/simd_constants.c','src/frameworks/ImageIO/src/CGImageLegacyConstants.c'],'artifacts/darling-imageio-matrix-source.patch'),
 ('vendor/darling/src/external/cocotron',['CoreGraphics/CMakeLists.txt','CoreGraphics/include/CoreGraphics/CoreGraphicsPrivate.h'],['CoreGraphics/CGFloat.c','CoreGraphics/CGContextNativeLayer.m','CoreGraphics/CGSAccelerator.c','CoreGraphics/CGImageIOConstants.c'],'artifacts/darling-imageio-cg-source.patch')]:
 patch=subprocess.check_output(['git','diff','--binary','--',*tracked],cwd=root/repo)
 for n in added:
  extra=subprocess.run(['git','diff','--no-index','--binary','--','/dev/null',n],cwd=root/repo,capture_output=True);assert extra.returncode==1;patch+=extra.stdout
 assert patch;temp=root/(out+'.pending');temp.write_bytes(patch);temp.replace(root/out);subprocess.run(['git','apply','--reverse','--check',str(root/out)],cwd=root/repo,check=True);patches.append(out)
evidence=list(paths.values())+patches+['artifacts/imageio-native-stage.json','artifacts/imageio-cg-constants-analysis.json','artifacts/imageio-cg-constants-stage.json','artifacts/simd-matrix-source-stage.json','artifacts/imageio-legacy-key-stage.json','artifacts/imageio-input-fixtures.json','config/cache-image-pins.json']
scripts=['rebuild-imageio-native.py','stage-imageio-native.py','imageio-native-profile.py','analyze-imageio-cg-constants.py','stage-imageio-cg-constants.py','stage-simd-matrix.py','stage-imageio-legacy-key.py','make-imageio-fixtures.py','probe-imageio-native.py','test-imageio-allocators.py','probe-native-layer-xcode.py','probe-native-lsd.py','record-imageio-progress.py']
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),previous_report='artifacts/mobilegestalt-progress.json',current_goal_turn_classification='progress',source_runtime=selected,implementation_form='Full original Intel ImageIO, 6522 exports/9814 functions, with ten original dependencies. Actual source-global metadata parsing is retained. Explicit typed C++ allocator import fallback ignores type tags. Added 34 actual-value CFString variables to Darling CoreGraphics sources and a 48-byte SIMD identity to Darling libm sources, built as individual components and named-reexported. Existing Darling-only ImageIO DPI key is preserved from source for AppKit; no native DPI option translation is claimed. Original xcodebuild is unchanged. Full CoreGraphics/libm/unified Darling builds are not performed.',evidence={n:digest(n) for n in evidence},scripts={'scripts/'+n:digest('scripts/'+n) for n in scripts},source_components={k:p[k] for k in ['imageio_cg_constants','simd_matrix','imageio_legacy_key']},imageio_native=p['imageio_native'],source_global_properties_cases=6,source_constant_values_verified=34,typed_allocator_allocations=896,native_lsd_UTI_verified=True,original_xcode_version_verified=True,sdk_listing_succeeded=False,next_original_xcode_loader_blocker=blocker,next_image_index_backend_blocker='_CGImageProviderCreate',goal_status='active',complete=False,full_xcode_build_ready=False,signing_ready=False,
 remaining_limits=[
 'Xcode SDK listing still exits 255 on Combine Just.setFailureType; no actual project build/archive/sign/export has succeeded.',
 'Native ImageIO source-global metadata works for the six checked PNG/GIF/TIFF data/URL cases. Image-index properties abort on missing CGImageProviderCreate. Real decode/pixels, JPEG, thumbnails, destinations, full metadata and private image-provider/block backends are not verified.',
 'Legacy Darling O2ColorSpaceCreateWithName reports an unimplemented path in the failing image-index test. Native ImageIO requires more than CFString keys for full CoreGraphics compatibility.',
 'The existing legacy ImageIO DPI key has unchanged bytes and satisfies the old AppKit import; converting that option into native destination properties is not implemented.',
 'Typed new/delete use the existing real standard allocator with scalar/array allocation/failure behavior tested; type-tag isolation is absent.',
 'Prior native MobileGestalt productType nil/device-name query failure and all previous platform/backend limitations remain. No ARM/Rosetta execution support is added.',
 'Only newly needed source components are independently compiled. The selected environment remains mixed source/native/compatibility libraries; default selection is unchanged.'])
destination='artifacts/imageio-native-progress.json';temp=root/(destination+'.pending');temp.write_text(json.dumps(record,indent=2)+'\n');temp.replace(root/destination)
state=read('artifacts/current-work-state.json');state.update(updated_at=record['checked_at'],primary_report=destination,goal_status='active',complete=False,latest_selected_runtime=selected,latest_implementation_form=record['implementation_form'],latest_xcode_loader_blocker=blocker,latest_staged_coreml_and_metal_blocker=blocker,active_build=dict(task='original-imageio-source-global-properties-and-source-constant-ABI',running=False,report=destination))
state['next_work']=list(dict.fromkeys([
 'Implement or restore actual Combine Just.setFailureType generic implementation and required Swift ABI/runtime metadata referenced by unchanged XCSourceControl. Do not provide a symbol-only return stub.',
 'Complete actual CoreGraphics image-provider/block and color-space backend for original ImageIO image-index properties, starting with CGImageProviderCreate. Current original source-global PNG/GIF/TIFF metadata works; real decode/pixels and image-index properties do not.',
]+[s for s in state['next_work'] if not s.startswith('Implement or restore actual ImageIO source-level properties')]))
state['last_verification']=list(dict.fromkeys(state['last_verification']+['Original ImageIO with eleven total original images now loads; six PNG/GIF/TIFF CFData/file-URL source-global property cases pass, including real FileSize and native GIF metadata. All 34 source CFString values and SIMD 48-byte layout pass runtime checks. Scalar/array typed allocation fallback passes 896 allocations and bad_alloc. Current original lsd/UTI and genuine xcodebuild -version pass. SDK listing now fails on Combine Just.setFailureType; image-index properties separately fail on CGImageProviderCreate.']))
state['latest_validation_reports']=list(dict.fromkeys(state['latest_validation_reports']+evidence+[destination]));state['source_components'].update(imageio_native='artifacts/imageio-native-stage.json',imageio_source_globals='artifacts/imageio-native-global-probe.json',imageio_coregraphics_constants='artifacts/imageio-cg-constants-stage.json',simd_matrix='artifacts/simd-matrix-source-stage.json',imageio_legacy_key='artifacts/imageio-legacy-key-stage.json',imageio_progress=destination)
temp=root/'artifacts/current-work-state.json.pending';temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(root/'artifacts/current-work-state.json');print('Recorded real native ImageIO properties and actual Combine SDK blocker; full goal remains active')
