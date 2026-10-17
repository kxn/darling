#!/usr/bin/env python3
"""Publish original Combine execution and the actual source inotify record fix."""

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
import hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') == 'artifacts/foundation-coherent-progress.json':
    print('Preserving the newer source selector/coherent Foundation/SDK checkpoint')
    raise SystemExit(0)

if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') == 'artifacts/fsevents-flush-progress.json':
    print('Preserving the newer source FSEvents flush checkpoint')
    raise SystemExit(0)

read=lambda n:json.loads((root/n).read_text());digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
p=runpy.run_path(str(root/'scripts/fsevents-source-profile.py'))['profile']();selected=p['source_runtime']
for v in selected.values():assert digest(v['path'])==v['sha256']
combine=p['combine_native'];reconstruction=read(combine['reconstruction']);assert combine['exports']==2023 and len(combine['objc_classes'])==4
assert reconstruction['code_analysis']['function_entries']==4362 and len(reconstruction['code_analysis']['tail_tables'])==180
assert not reconstruction['redirected_imports'] and not reconstruction['backend_call_overrides']
assert reconstruction['swift_metadata']['contexts']==390 and reconstruction['swift_metadata']['generic_contexts']==255 and reconstruction['swift_metadata']['conformances']==725
for key in ['original','source','library','reconstruction']:assert digest(combine[key])==combine[key+'_sha256']
fs=p['source_fsevents'];assert fs['full_FSEvents_source_component_build'] and fs['complete_source_files']==2 and fs['original_exports_preserved']==fs['source_exports']==29 and not fs['flush_async_implemented']
for n,sha in {**fs['sources'],**fs['headers']}.items():assert digest(n)==sha
paths={'combine':'artifacts/combine-native-test.json','baseline':'artifacts/fsevents-baseline-probe.json','source_burst':'artifacts/fsevents-source-burst-probe.json','version':'artifacts/fsevents-source-xcode-version.json','showsdks':'artifacts/fsevents-source-xcode-showsdks.json','lsd':'artifacts/native-lsd-fsevents-source-probe.json'}
results={k:read(n) for k,n in paths.items()};common=['combine_native','imageio_native','imageio_cg_constants','simd_matrix','imageio_legacy_key','runnable_archs','source_libdyld','mobilegestalt_native']
for name,r in results.items():
 assert r['source_runtime']==selected
 for key in common:assert r[key]==p[key]
 if name not in ['combine','baseline']:assert r['source_fsevents']==fs
 if 'log' in r:assert digest(r['log'])==r['log_sha256']
 for n,sha in r.get('logs',{}).items():assert digest(n)==sha
 if name in ['source_burst','version','lsd']:assert r['exit_status']==0
c=results['combine'];assert c['runtime_execution_verified'] and c['original_Apple_SDK_interface_used'] and not c['full_Combine_compatibility']
assert [x['step'] for x in c['checks']]==['compile','link','execute']
for r in c['checks']:assert r['exit_status']==0 and digest(r['log'])==r['log_sha256']
for n,sha in {**c['sources'],**c['binaries']}.items():assert digest(n)==sha
text=(root/c['checks'][-1]['log']).read_text()
for marker in ['COMBINE_NATIVE_ORIGINAL_SET_FAILURE_TYPE_OWNER_OK','COMBINE_MAP_CATCH_FUTURE_DEMAND_CANCEL_OK','NATIVE_COMBINE_JUST_SET_FAILURE_TYPE_REAL_RESULT_PUBLISHER_GENERIC_VALUES_OK cases=10','NATIVE_COMBINE_REFERENCE_PAYLOAD_OWNERSHIP_OK','NATIVE_COMBINE_XCSOURCECONTROL_TYPED_TRYMAP_FLATMAP_ERASURE_STORE_SUCCESS_FAILURE_OK cases=64','NATIVE_COMBINE_PUBLISHED_REFLECTION_OBSERVABLE_OBJECT_CHANGE_AND_CANCEL_OK','NATIVE_COMBINE_ALL_CHECKED_SEMANTICS_OK']:assert marker in text
assert 'is implemented in both' not in text
imports=read('artifacts/xcsourcecontrol-combine-imports.json');assert imports['all_imports_present'] and not imports['missing'] and len(imports['imports'])==25 and digest(imports['client'])==imports['client_sha256'] and imports['provider_sha256']==combine['library_sha256']
exports=set(re.findall(r'^0x[0-9A-Fa-f]+\s+(\S+)',subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(root/combine['library'])],text=True),re.M))
assert set((root/'artifacts/dvtfoundation-combine-imports.txt').read_text().splitlines())<=exports
counts={}
for name in ['baseline','source_burst']:
 r=results[name];assert digest('fixtures/hello/fsevents-baseline.m')==r['source_sha256'] and digest('artifacts/fsevents-baseline')==r['binary_sha256']
 text=(root/r['log']).read_text();m=re.search(r'expected=64 unique_paths=(\d+) waited=(\d+) latest=(\d+)',text);assert m and int(m[2])==0
 counts[name]=dict(unique_paths=int(m[1]),event_id=int(m[3]));assert 'FSEVENTS_BASELINE_FLUSH_ASYNC_PRESENT 0' in text
assert results['baseline']['exit_status']==1 and not results['baseline']['complete_delivery_verified'] and 0<counts['baseline']['unique_paths']<64
assert counts['source_burst']==dict(unique_paths=64,event_id=128) and results['source_burst']['complete_delivery_verified']
assert '/runtime/fsevents-source/frameworks/' in (root/results['source_burst']['log']).read_text()
assert 'Xcode 26.6\nBuild version 17F113' in (root/results['version']['log']).read_text()
blocker='_FSEventStreamFlushAsync';assert results['showsdks']['exit_status']==255 and 'Symbol not found: '+blocker in (root/results['showsdks']['log']).read_text()
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild';assert digest(original)==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
for name in ['version','showsdks']:assert results[name]['original_xcodebuild_sha256']==digest(original)
lsd=results['lsd'];assert lsd['UTI_functional_execution_verified'] and not lsd['frozen_trace_comparison'] and 'NATIVE_UTI_TYPED_TAG_CONFORMANCE_AND_URL_EXTENSION_OK' in lsd['diagnostic']
assert 'Symbol not found:' not in lsd['daemon_diagnostic'] and 'Error -43 registering path /System/Library/CoreServices/CoreTypes.bundle' not in lsd['daemon_diagnostic']
for arg in p['command']:
 if arg.startswith(('DYLD_LIBRARY_PATH=','DYLD_FRAMEWORK_PATH=')):
  k,v=arg.split('=',1);assert lsd['selected_job']['EnvironmentVariables'][k]==v
source='src/frameworks/CoreServices/src/FSEvents/FSEventsImpl.m';patch=subprocess.check_output(['git','diff','--binary','--',source],cwd=root/'vendor/darling');assert patch
out='artifacts/darling-fsevents-read-records-source.patch';temp=root/(out+'.pending');temp.write_bytes(patch);temp.replace(root/out);subprocess.run(['git','apply','--reverse','--check',str(root/out)],cwd=root/'vendor/darling',check=True)
evidence=list(paths.values())+[out,'artifacts/combine-native-stage.json','runtime/rebuilt-combine-native/reconstruction.json','artifacts/xcsourcecontrol-combine-imports.json','artifacts/dvtfoundation-combine-imports.txt','artifacts/fsevents-source-build.json','artifacts/fsevents-source-next-analysis.json','logs/fsevents-baseline-first-loss.log','config/cache-image-pins.json']
scripts=['stage-combine-native.py','combine-native-profile.py','test-combine-native.py','build-fsevents-source.py','fsevents-source-profile.py','probe-fsevents-baseline.py','probe-native-layer-xcode.py','probe-native-lsd.py','record-combine-fsevents-progress.py']
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),previous_report='artifacts/imageio-native-progress.json',previous_goal_turn_classification='progress',current_goal_turn_classification='progress',source_runtime=selected,combine_native=combine,source_fsevents=fs,evidence={n:digest(n) for n in evidence},scripts={'scripts/'+n:digest('scripts/'+n) for n in scripts},source_burst_comparison=counts,original_sdk_semantics_verified=True,original_xcode_version_verified=True,original_lsd_UTI_verified=True,sdk_listing_succeeded=False,next_original_xcode_loader_blocker=blocker,goal_status='active',complete=False,full_xcode_build_ready=False,signing_ready=False,
 implementation_form='Complete original Intel Combine with 2023 exports, 4362 functions, 390 recovered Swift contexts and four actual ObjC-visible Swift classes; no backend override or imported-function redirect. It replaces the earlier OpenCombine provider only in this private profile. Complete two-file Darling source FSEvents preserves all 29 old exports and now processes every variable-length inotify record in a read buffer. This is a real source fix; FlushAsync is not implemented. The prior source/native/compatibility environment remains and original xcodebuild is unchanged.',
 remaining_limits=[
 'SDK listing exits 255 on FSEventStreamFlushAsync. Complete project build/archive/sign/export has not succeeded.',
 'Original Combine selected typed Result, ownership, backpressure/cancellation, Future and map/catch, source-control tryMap/flatMap/erasure/store, and Published/ObservableObject reflection tests pass. All other operators, schedulers, concurrent execution and full Xcode consumer behavior are not established by these tests.',
 'FSEvents still lacks async/sync flush entries, true requested latency, immutable cross-queue callback batch ownership, recursive watch coverage, persistent/global event IDs and full restart/invalidation guarantees. The source read fix does not claim any of these.',
 'Original ImageIO source-global properties remain verified; image-index properties and decode still need CGImageProviderCreate and actual color-space/provider backends.',
 'Previous native MobileGestalt identity/device-name, metadata, sandbox policy, signing/trust, window/GPU and XPC limitations remain. Default runtime selection is unchanged; no unified full Darling rebuild is claimed.'])
destination='artifacts/combine-fsevents-progress.json';temp=root/(destination+'.pending');temp.write_text(json.dumps(record,indent=2)+'\n');temp.replace(root/destination)
state=read('artifacts/current-work-state.json');state.update(updated_at=record['checked_at'],primary_report=destination,goal_status='active',complete=False,latest_selected_runtime=selected,latest_implementation_form=record['implementation_form'],latest_xcode_loader_blocker=blocker,latest_staged_coreml_and_metal_blocker=blocker,active_build=dict(task='original-combine-and-source-inotify-records',running=False,report=destination))
state['next_work']=list(dict.fromkeys([
 'Implement actual FSEventStreamFlushAsync in Darling FSEvents source. Keep real FD draining and all-record iteration; introduce immutable callback batches and queue/run-loop ordering so flush cannot reallocate an active callback buffer. Return the actual largest queued id, preserve real errors, and test delayed real filesystem mutations, callback reentrancy, latency and lifecycle. Do not add a return-only export.',
]+[s for s in state['next_work'] if not s.startswith('Implement or restore actual Combine Just.setFailureType')]))
state['last_verification']=list(dict.fromkeys(state['last_verification']+['Original Intel Combine replaces the earlier source compatibility provider in a private profile: 2023 exports, 4362 functions, 390 Swift contexts. Apple SDK client passes typed Just/Result for ten scalar/string/struct values, reference ownership, map/catch/Future/backpressure/cancel, 64 source-control tryMap/flatMap/erasure/store success/failure cases and Published/ObservableObject reflection. Full two-file source FSEvents fixes variable-length inotify record loss: same 64-file client receives 64 paths/128 IDs; packaged baseline receives 30 paths/30 IDs. Final original lsd/UTI and xcodebuild -version pass; -showsdks still lacks FSEventStreamFlushAsync.']))
state['latest_validation_reports']=list(dict.fromkeys(state['latest_validation_reports']+evidence+[destination]));state['source_components'].update(combine_native='artifacts/combine-native-stage.json',combine_native_execution='artifacts/combine-native-test.json',fsevents='artifacts/fsevents-source-build.json',fsevents_read_execution='artifacts/fsevents-source-burst-probe.json',combine_fsevents_progress=destination)
temp=root/'artifacts/current-work-state.json.pending';temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(root/'artifacts/current-work-state.json');print('Recorded original Combine and actual source inotify record fix; full Xcode goal remains active')
