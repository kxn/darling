#!/usr/bin/env python3
"""Check and publish source layers/native logging evidence without claiming Xcode success."""

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

if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') == 'artifacts/imageio-native-progress.json':
    print('Preserving the newer original ImageIO/source-ABI checkpoint')
    raise SystemExit(0)

if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') == 'artifacts/mobilegestalt-progress.json':
    print('Preserving the newer MobileGestalt/source-dyld checkpoint')
    raise SystemExit(0)

if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') == 'artifacts/log-hooks-progress.json':
    print('Preserving the newer source log-hook checkpoint')
    raise SystemExit(0)

read=lambda p:json.loads((root/p).read_text())
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
p=runpy.run_path(str(root/'scripts/native-log-message-profile.py'))['profile']()
stages={k:p[k] for k in ['native_layer_support','native_layer_context','log_enablement','native_log_message']}
selected=p['source_runtime']
for v in selected.values():assert digest(v['path'])==v['sha256']
assert p['source_kernel']['complete_source_files']==875
assert stages['native_layer_context']['export_changes']['original_instructions_and_other_bytes_preserved']
for name in ['log_enablement','native_log_message']:
 assert stages[name]['export_changes']['original_instructions_and_other_bytes_preserved']
 assert not stages[name]['export_changes']['provider_entire_namespace_reexported']
trace=stages['log_enablement']['source_build'];assert trace['complete_source_files']==8 and trace['full_libtrace_source_build']
assert trace['original_exports_preserved']==142 and trace['source_exports']==144
tests={
 'render':'artifacts/native-calayer-render-source-support-probe.json',
 'context':'artifacts/native-layer-context-test.json',
 'scalars':'artifacts/layer-log-scalars-test.json',
 'appkit':'artifacts/native-layer-appkit-test.json',
 'trace':'artifacts/libtrace-enablement-execution.json',
 'message':'artifacts/native-log-message-system-probe.json',
 'version':'artifacts/native-message-xcode-version.json',
 'showsdks':'artifacts/native-message-xcode-showsdks.json',
 'lsd':'artifacts/native-lsd-native-message-layer-log-mount-path-container-manager-metadata-kernel-sysdir-paired-dirhelper-sandbox-container-datavault-user-local-dir-source-libtrace-probe.json'}
results={k:read(v) for k,v in tests.items()}
for name,r in results.items():
 assert r['source_runtime']==selected
 if 'log' in r:assert digest(r['log'])==r['log_sha256']
 for path,sha in r.get('logs',{}).items():assert digest(path)==sha
 if name!='showsdks':assert r['exit_status']==0
 for key,value in stages.items():
  if key in r:assert r[key]==value,(name,key)
for name,source,binary in [
 ('render','fixtures/hello/native-calayer-render.m','artifacts/native-calayer-render'),
 ('context','fixtures/hello/native-layer-context.m','artifacts/native-layer-context'),
 ('scalars','fixtures/hello/layer-log-scalars.m','artifacts/layer-log-scalars'),
 ('appkit','fixtures/hello/native-layer-appkit.m','artifacts/native-layer-appkit'),
 ('message','fixtures/hello/native-log-message.c','artifacts/native-log-message')]:
 r=results[name];assert r['source_sha256']==digest(source) and r['binary_sha256']==digest(binary)
assert results['trace']['test_source_sha256']==digest('fixtures/hello/libtrace-source.m')
assert results['trace']['test_binary_sha256']==digest('artifacts/libtrace-enablement')
assert results['trace']['build']==trace and results['trace']['runtime_execution_verified']
assert results['trace']['actual_ASL_stderr_record_text_verified']
text=lambda name:(root/results[name]['log']).read_text()
assert 'NATIVE_LAYER_REAL_BITMAP_TREE_RENDER_OK' in text('render')
assert 'SOURCE_CALAYER_CONTEXT_BITMAP_TREE_SNAPSHOT_RESIZE_CLEAR_ERRORS_AND_TIMER_OK 31' in text('context')
assert 'CGFLOAT_NATIVE_DIFFERENTIAL_AND_FP_FLAGS_OK values=18206' in text('scalars')
assert 'LOG_COMPARE_ALL_25_ORIGINAL_INSTRUCTION_RESULTS_AND_SOURCE_OWNER_OK' in text('scalars')
assert 'BASE_CTM_INDEPENDENT_RENDER_STATE_GSTATE_AND_TRANSFORMED_PIXELS_OK' in text('scalars')
assert results['scalars']['reference_analysis_sha256']==digest('artifacts/layer-log-native-analysis.json')
assert 'REAL_DARLING_NSVIEW_HOSTED_AND_BACKING_LAYER_CONTEXT_PIXELS_RESIZE_AND_TEARDOWN_OK' in text('appkit')
assert 'LIBSYSTEM_MESSAGE_IMPORT_USES_VERIFIED_FORWARDER' in text('message')
assert 'NATIVE_MESSAGE_RESULT hidden=<private>' in text('message')
assert text('message').count('NATIVE_MESSAGE_RESULT hidden=secret')==2
assert 'ORIGINAL_LOG_MESSAGE_LITERAL_PUBLIC_SCALARS_AND_SERIALIZED_STRING_OK' in text('message')
assert results['lsd']['UTI_functional_execution_verified']
assert results['lsd']['source_libtrace']==trace
assert 'NATIVE_UTI_TYPED_TAG_CONFORMANCE_AND_URL_EXTENSION_OK' in results['lsd']['diagnostic']
assert 'Error -43 registering path /System/Library/CoreServices/CoreTypes.bundle' not in results['lsd']['daemon_diagnostic']
for v in p['command']:
 if v.startswith(('DYLD_LIBRARY_PATH=','DYLD_FRAMEWORK_PATH=')):
  key,value=v.split('=',1);assert results['lsd']['selected_job']['EnvironmentVariables'][key]==value
assert 'Xcode 26.6\nBuild version 17F113' in text('version')
assert results['showsdks']['exit_status']==255 and 'Symbol not found: _os_log_set_hook' in text('showsdks')
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
assert digest(original)==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
for mode in ['version','showsdks']:assert results[mode]['original_xcodebuild_sha256']==digest(original)
patches=[];source_files={}
for repo,tracked,added,destination in [
 ('vendor/darling/src/external/cocotron',
  ['CoreGraphics/CMakeLists.txt','CoreGraphics/include/CoreGraphics/CoreGraphicsPrivate.h','QuartzCore/CMakeLists.txt','QuartzCore/include/QuartzCore/CALayerContext.h'],
  ['CoreGraphics/CGFloat.c','CoreGraphics/CGContextNativeLayer.m','CoreGraphics/CGSAccelerator.c','QuartzCore/CALayerContextNative.m','QuartzCore/CARenderServer.m','QuartzCore/private-include/QuartzCore/CARenderServer.h'],
  'artifacts/darling-native-layer-source.patch'),
 ('vendor/darling/src/external/libtrace',
  ['libsystem_trace/os_log.c','include/os/log_private.h','libsystem_trace/unpack_buffer.m','libsbuf/libsbuf.c'],[],
  'artifacts/darling-libtrace-enablement-source.patch')]:
 work=root/repo;patch=subprocess.check_output(['git','diff','--binary','--',*tracked],cwd=work)
 for path in added:
  assert subprocess.run(['git','ls-files','--error-unmatch',path],cwd=work,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
  extra=subprocess.run(['git','diff','--no-index','--binary','--','/dev/null',path],cwd=work,capture_output=True);assert extra.returncode==1;patch+=extra.stdout
 pending=root/(destination+'.pending');pending.write_bytes(patch);pending.replace(root/destination)
 subprocess.run(['git','apply','--reverse','--check',str(root/destination)],cwd=work,check=True)
 patches.append(destination)
 for name in tracked+added:source_files[repo+'/'+name]=digest(repo+'/'+name)
evidence=list(tests.values())+patches+['artifacts/native-layer-support-stage.json','artifacts/native-layer-context-stage.json','artifacts/libtrace-enablement-source-build.json','artifacts/log-enablement-stage.json','artifacts/native-log-message-stage.json','artifacts/layer-log-native-analysis.json','artifacts/native-log-message-analysis.json']
for path in ['artifacts/layer-log-native-analysis.json','artifacts/native-log-message-analysis.json']:
 r=read(path);assert digest(r['log'])==r['log_sha256']
scripts=['stage-native-layer-support.py','stage-native-layer-context.py','native-layer-profile.py','native-layer-context-profile.py','analyze-layer-log-native.py','analyze-native-log-message.py','test-layer-log-scalars.py','test-native-layer-context.py','test-native-layer-appkit.py','probe-native-calayer-render.py','build-libtrace-source.py','test-libtrace-source.py','stage-log-enablement.py','log-enablement-profile.py','native-log-message-loader.c','stage-native-log-message.py','native-log-message-profile.py','probe-native-log-message.py','probe-native-layer-xcode.py','probe-native-lsd.py','record-layer-log-progress.py']
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),previous_report='artifacts/mount-container-progress.json',previous_turn_classification='no progress: clarified implementation form only',current_turn_classification='progress',selected_runtime=selected,
 evidence={name:digest(name) for name in evidence},source_files=source_files,scripts={'scripts/'+name:digest('scripts/'+name) for name in scripts},
 original_xcodebuild_sha256=digest(original),native_CALayer_tree_pixels_verified=True,source_CALayerContext_pixels_ownership_resize_timer_and_errors_verified=True,original_Darling_NSView_layer_caller_verified=True,
 CGFloat_native_differential_values=18206,all_25_log_ordering_results_verified=True,actual_nonidentity_context_state_and_pixels_verified=True,
 source_libtrace_files_compiled=8,original_native_log_message_formatter_verified=True,original_LaunchServices_and_complete_current_UTI_fixture_verified=True,
 original_xcode_version_verified=True,sdk_listing_verified=False,full_xcode_build_ready=False,signing_ready=False,installed_as_default=False,full_darling_rebuild=False,
 current_blocker='Original XCTestCore import _os_log_set_hook; os_log_get_type and os_log_set_fault_callback are also still unimplemented source stubs.',
 implementation_form='Direct Cocotron CoreGraphics state/scalar helpers and real offscreen CALayerContext source, original native CALayer rendering, complete 8-file source libtrace with correct log-level comparator, and an exact deferred call to the existing original native message formatter. Private named reexports preserve original QuartzCore and libSystem instructions. Original Xcode is unchanged; this is not yet a unified full Darling build.',
 limits=[
  'Bitmap rendering and the actual NSView caller are verified. Native window attachment, OpenGL textures, Metal devices, display-server composition and full AppKit drawing are not implemented by this context.',
  'Base CTM metadata remains separate from physical Onyx geometry and graphics-state save/restore, matching the inspected native storage contract. Selected nonidentity state/pixel cases pass; general QuartzCore drawing and GPU behavior are unproven.',
  'The native formatter receives the original message record unchanged. A supplied private payload is formatted; an absent private pool produces <private>. This function does not implement or claim collection-time privacy authorization.',
  'Only the existing original native metrics classes are registered; legacy native log/activity classes remain excluded to preserve Darling logging. Loading is lazy; eager loading still exposes an unsupported __dyld_dlsym_blocked dependency in LoggingSupport.',
  'Logging hooks must deliver actual events, retain callback ownership correctly and agree with native message layout. Merely registering a callback in isolated native trace state would not connect Darling-produced events.',
  'Earlier filesystem, container policy and LaunchServices limits remain. Current lsd/UTI behavior is preserved; translocation and full protected container services remain incomplete.',
  'Default launcher is unchanged. Genuine SDK listing still fails, and project build/archive/sign/export have not passed.'])
destination='artifacts/layer-log-progress.json';pending=root/(destination+'.pending');pending.write_text(json.dumps(record,indent=2)+'\n');pending.replace(root/destination)
state=read('artifacts/current-work-state.json')
state.update(updated_at=record['checked_at'],primary_report=destination,goal_status='active',complete=False,active_build=dict(task='source-native-layer-and-log-formatting',running=False,report=destination),latest_selected_runtime=selected,latest_implementation_form=record['implementation_form'],
 latest_staged_coreml_and_metal_blocker=record['current_blocker'])
state['next_work']=[
 'Implement real source logging hooks needed by original XCTestCore: verify native registration ABI, block ownership, level filtering, fault callback and message getters; connect actual Darling-emitted records and serialized payload lifetimes. Do not use an empty hook or disconnected native registration as success.',
 'Continue genuine unchanged xcodebuild -showsdks after logging integration, then original project build/archive/sign/export with CocoaPods and Unity-generated Xcode inputs as required.',
]+[s for s in state['next_work'] if not s.startswith(('Resolve genuine xcodebuild -showsdks loader blocker CALayerContext','Resolve the real CALayerContext dependency'))]
state['last_verification'].append('Real source bitmap CALayerContext and original NSView rendering pass; 18206 native scalar differentials, 25 native log orderings, transformed context pixels, complete source libtrace regression and original formatter payload/private-pool tests pass. Latest original lsd/UTI and xcodebuild -version pass; -showsdks now fails on os_log_set_hook. Full Xcode goal remains active.')
state['latest_validation_reports']=list(dict.fromkeys(state['latest_validation_reports']+evidence+[destination]))
state.setdefault('source_components',{}).update(native_layer='artifacts/native-layer-context-stage.json',native_layer_graphics='artifacts/native-layer-support-stage.json',libtrace='artifacts/libtrace-enablement-source-build.json',native_log_message='artifacts/native-log-message-stage.json',layer_log_progress=destination)
pending=root/'artifacts/current-work-state.json.pending';pending.write_text(json.dumps(state,indent=2)+'\n');pending.replace(root/'artifacts/current-work-state.json')
print('Recorded source native layer and original log formatter progress; full Xcode goal remains active')
