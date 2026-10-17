#!/usr/bin/env python3
"""Publish actual source flush behavior and the next original initialization error."""

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

read=lambda n:json.loads((root/n).read_text());digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
p=runpy.run_path(str(root/'scripts/fsevents-flush-profile.py'))['profile']();selected=p['source_runtime'];fs=p['source_fsevents']
assert fs['full_FSEvents_source_component_build'] and fs['complete_source_files']==2 and fs['original_exports_preserved']==29 and fs['source_exports']==57
assert fs['flush_async_implemented'] and fs['flush_sync_implemented'] and fs['immutable_callback_batches'] and fs['weak_source_contexts']
for n,sha in {**fs['sources'],**fs['headers']}.items():assert digest(n)==sha
for key in ['original','library']:assert digest(fs[key])==fs[key+'_sha256']
for v in selected.values():assert digest(v['path'])==v['sha256']
paths={'test':'artifacts/fsevents-flush-test.json','repeats':'artifacts/fsevents-flush-repeats.json','version':'artifacts/fsevents-flush-xcode-version.json','showsdks':'artifacts/fsevents-flush-xcode-showsdks.json','lsd':'artifacts/native-lsd-fsevents-flush-probe.json','owner':'artifacts/objc-selected-owner-probe.json'}
results={k:read(n) for k,n in paths.items()}
for name,r in results.items():
 assert r['source_runtime']==selected and r['source_fsevents']==fs
 for key in ['combine_native','imageio_native','imageio_cg_constants','simd_matrix','imageio_legacy_key','runnable_archs','source_libdyld','mobilegestalt_native']:assert r[key]==p[key]
 if 'log' in r:assert digest(r['log'])==r['log_sha256']
 for n,sha in r.get('logs',{}).items():assert digest(n)==sha
 if name not in ['showsdks','repeats']:assert r['exit_status']==0
r=results['test'];assert r['runtime_execution_verified'] and r['source_sha256']==digest('fixtures/hello/fsevents-flush.m') and r['binary_sha256']==digest('artifacts/fsevents-flush')
text=(root/r['log']).read_text()
markers=['ASYNC_REAL_BURST_WATERMARK_AND_THREE_PAYLOAD_FORMATS','CALLBACK_FLUSH_REAL_MUTATION_AND_IMMUTABLE_ACTIVE_BUFFERS','REQUESTED_LATENCY_TIMER_ACTUAL_DELIVERY','CALLBACK_STOP_AND_REAL_PENDING_RESTART','REAL_RUN_LOOP_MODE_AND_ASYNC_FLUSH','INVALIDATION_DROPS_PENDING_CALLBACKS_AND_CLOSES_ACTUAL_FD','SYNC_CALLBACK_COMPLETION_AND_SAME_QUEUE_NO_DEADLOCK','REENTRANT_SYNC_FLUSH_ACTUAL_NESTED_CALLBACKS','SYNC_WAITS_FOR_REAL_SUSPENDED_QUEUE_DELIVERY','SYNC_OWN_AND_FOREIGN_THREAD_RUN_LOOP_DELIVERY','NO_DEFER_IDLE_IMMEDIATE_AND_REAL_LATENCY_COALESCING','FOUR_CONCURRENT_FLUSHERS_AND_CONCURRENT_DELIVERY_QUEUE_FIFO','INVALIDATE_FROM_CALLBACK_BALANCED_CONTEXT_AND_FD','LAST_RELEASE_WITHOUT_START_OR_INVALIDATE_CLOSES_FD']
for marker in markers:assert 'SOURCE_FSEVENTS_'+marker+'_OK' in text
assert 'SOURCE_FSEVENTS_FLUSH_ALL_CHECKED_SEMANTICS_OK checks=88' in text
r=results['repeats'];assert r['all_three_repeats_verified'] and len(r['checks'])==3
assert r['binary_sha256']==digest('artifacts/fsevents-flush') and r['source_sha256']==digest('fixtures/hello/fsevents-flush.m')
for c in r['checks']:assert c['verified'] and c['exit_status']==0 and c['log_sha256']==digest(c['log'])
assert 'Xcode 26.6\nBuild version 17F113' in (root/results['version']['log']).read_text()
blocker='Objective-C selector backend UUID/code/layout guard rejected incompatible runtime';diagnostic=(root/results['showsdks']['log']).read_text()
assert results['showsdks']['exit_status']==1 and blocker in diagnostic
assert 'Symbol not found: _FSEventStreamFlushAsync' not in diagnostic and 'Symbol not found: _FSEventStreamFlushSync' not in diagnostic
assert 'NSConstantFloatNumber is implemented in both' in diagnostic and '/usr/lib/swift/libswiftFoundation.dylib' in diagnostic
analysis=read('artifacts/fsevents-flush-next-runtime-analysis.json');assert not analysis['UUIDs_match'] and analysis['owner_runtime_verified']
assert digest(analysis['selected_objc'])==analysis['selected_objc_sha256'] and digest(analysis['guard_config'])==analysis['guard_config_sha256'] and digest(analysis['guard_implementation'])==analysis['guard_implementation_sha256']
r=results['owner'];assert r['runtime_execution_verified'] and r['source_sha256']==digest('fixtures/hello/objc-selected-owner.c') and r['binary_sha256']==digest('artifacts/objc-selected-owner')
assert 'SELECTED_OBJC_UUID '+analysis['selected_uuid'] in (root/r['log']).read_text()
lsd=results['lsd'];assert lsd['UTI_functional_execution_verified'] and not lsd['frozen_trace_comparison'];assert 'NATIVE_UTI_TYPED_TAG_CONFORMANCE_AND_URL_EXTENSION_OK' in lsd['diagnostic']
assert 'Symbol not found:' not in lsd['daemon_diagnostic'] and 'Error -43 registering path /System/Library/CoreServices/CoreTypes.bundle' not in lsd['daemon_diagnostic']
for arg in p['command']:
 if arg.startswith(('DYLD_LIBRARY_PATH=','DYLD_FRAMEWORK_PATH=')):
  k,v=arg.split('=',1);assert lsd['selected_job']['EnvironmentVariables'][k]==v
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild';assert digest(original)==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
for name in ['version','showsdks']:assert results[name]['original_xcodebuild_sha256']==digest(original)
files=['src/frameworks/CoreServices/src/FSEvents/FSEvents.m','src/frameworks/CoreServices/src/FSEvents/FSEventsImpl.m','src/frameworks/CoreServices/src/FSEvents/FSEventsImpl.h','src/frameworks/CoreServices/src/FSEvents/CMakeLists.txt','src/frameworks/CoreServices/include/FSEvents/FSEvents.h']
patch=subprocess.check_output(['git','diff','--binary','--',*files],cwd=root/'vendor/darling');assert patch
out='artifacts/darling-fsevents-flush-source.patch';temp=root/(out+'.pending');temp.write_bytes(patch);temp.replace(root/out);subprocess.run(['git','apply','--reverse','--check',str(root/out)],cwd=root/'vendor/darling',check=True)
historical_logs=['logs/fsevents-flush-first-sync-timeout.log','logs/fsevents-flush-debug-test.log','logs/fsevents-flush-debug-all-frames.log','logs/fsevents-flush-debug-current-maps.log']
assert 'FSSYNC' in (root/'logs/fsevents-flush-debug-test.log').read_text() and 'done' in (root/'logs/fsevents-flush-debug-test.log').read_text()
evidence=list(paths.values())+[out,'artifacts/fsevents-flush-source-build.json','artifacts/fsevents-flush-next-runtime-analysis.json']+historical_logs
scripts=['build-fsevents-source.py','fsevents-flush-profile.py','test-fsevents-flush.py','repeat-fsevents-flush.py','probe-objc-selected-owner.py','probe-native-layer-xcode.py','probe-native-lsd.py','record-fsevents-flush-progress.py']
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),previous_report='artifacts/combine-fsevents-progress.json',previous_goal_turn_classification='progress',current_goal_turn_classification='progress',source_runtime=selected,source_fsevents=fs,evidence={n:digest(n) for n in evidence},scripts={'scripts/'+n:digest('scripts/'+n) for n in scripts},explicit_counted_checks_per_run=88,final_additional_repetitions=3,version_succeeded=True,native_lsd_UTI_succeeded=True,sdk_listing_succeeded=False,next_original_xcode_failure=blocker,next_original_xcode_failure_kind='initialization_runtime_guard',goal_status='active',complete=False,full_xcode_build_ready=False,signing_ready=False,
 implementation_form='Actual two-file Darling source FSEvents with new public async/sync flush entries, per-stream state serialization, immutable callback payloads, requested latency/NoDefer timers, weak dispatch/run-loop contexts, callback reentrancy and FD/context cleanup including last release and CLOEXEC. All 29 previous exports are preserved; the source component now exports 57 symbols. No return-only shim or synthetic filesystem success is used. Other source/native/compatibility layers and the unchanged original Xcode remain.',
 remaining_limits=[
 'Actual xcodebuild -showsdks now exits 1 during initialization because the old Objective-C selector adapter guard rejects the selected rebuilt source runtime. The guard is not removed or weakened. The owner and unequal UUIDs are verified.',
 'The same original initialization logs duplicate NSConstantFloatNumber and Swift Foundation classes from native Foundation and old compatibility providers. Current Foundation composition must be made coherent; importing all framework symbols does not prove initialization compatibility.',
 'Early expanded tests hung in a native CoreFoundation run-loop wait even after the foreign flusher logged completion; captured GDB frames are retained. The final foreign-thread flush test stops the run loop explicitly on completion and passes three repetitions. Standalone timeout probes passed, but the complex timed-run-loop failure is not diagnosed or fixed.',
 'Recursive subtree watches, durable/global event IDs/history, relative-device streams, all creation/event flags, file-ID extended data and dropped-event/rename fidelity are incomplete or not fully verified. The added overflow branch is not validated by an actual kernel-overflow test.',
 'The independently compiled FSEvents component is not a unified Darling distribution build. The default launcher selection is unchanged. No full project build/archive/sign/export is verified.',
 'Previous image-provider/decode, native device-identity, metadata, sandbox policy, certificate trust/signing, graphics/window and XPC limitations remain.'])
destination='artifacts/fsevents-flush-progress.json';temp=root/(destination+'.pending');temp.write_text(json.dumps(record,indent=2)+'\n');temp.replace(root/destination)
state=read('artifacts/current-work-state.json');state.update(updated_at=record['checked_at'],primary_report=destination,goal_status='active',complete=False,latest_selected_runtime=selected,latest_implementation_form=record['implementation_form'],latest_xcode_loader_blocker=blocker,latest_xcode_runtime_failure=blocker,latest_xcode_failure_kind=record['next_original_xcode_failure_kind'],latest_staged_coreml_and_metal_blocker=blocker,active_build=dict(task='source-fsevents-flush-and-real-callback-lifecycle',running=False,report=destination))
state['next_work']=list(dict.fromkeys([
 'Implement sel_lookUpByName in the actual Darling Objective-C runtime over its real selector set and lock, and replace the old UUID-coupled lookup adapter in the selected Foundation composition. The current adapter correctly rejects the selected source runtime. Preserve unknown-name/no-registration and concurrency semantics; do not weaken the guard.',
 'Make native Foundation initialization coherent: use the actual modern libswiftFoundation reexport shim and native NSConstantFloatNumber class, removing duplicate old compatibility definitions only after owner/ABI/behavior tests. Continue unchanged original xcodebuild -showsdks through real initialization.',
 'Diagnose the retained complex timed-run-loop failure. Foreign source flush completion is logged while native CFRunLoopRun / CFRunLoopServiceMachPort remains waiting. Simple native timeout probes pass; final flush tests use explicit completion-stop and do not prove the failing timeout scenario is fixed.',
]+[s for s in state['next_work'] if not s.startswith('Implement actual FSEventStreamFlushAsync')]))
state['last_verification']=list(dict.fromkeys(state['last_verification']+['Complete source FSEvents async/sync flush with immutable batches and actual inotify FD delivery passes 88 counted checks plus payload/event assertions, with three additional full repetitions. Tests cover three payload formats, 64-file bursts, callback async/sync reentry, suspended/same/concurrent queues, real latency/NoDefer, run-loop delivery, stop/restart, invalidate and last-release FD/context cleanup including CLOEXEC. Final original lsd/UTI and xcodebuild -version pass; SDK listing reaches initialization and fails the old selector adapter guard, with Foundation duplicate classes. Complex timed-run-loop timeout behavior remains unresolved.']))
state['latest_validation_reports']=list(dict.fromkeys(state['latest_validation_reports']+evidence+[destination]));state['source_components'].update(fsevents='artifacts/fsevents-flush-source-build.json',fsevents_flush_execution='artifacts/fsevents-flush-test.json',fsevents_flush_repeats='artifacts/fsevents-flush-repeats.json',selected_objc_owner='artifacts/objc-selected-owner-probe.json',fsevents_flush_progress=destination)
temp=root/'artifacts/current-work-state.json.pending';temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(root/'artifacts/current-work-state.json');print('Recorded actual source flush behavior and guarded original initialization failure; goal remains active')
