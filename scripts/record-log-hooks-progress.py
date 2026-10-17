#!/usr/bin/env python3
"""Publish verified source logging progress and the next genuine loader failure."""

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

if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') == 'artifacts/combine-fsevents-progress.json':
    print('Preserving the newer original Combine/source FSEvents checkpoint')
    raise SystemExit(0)

if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') == 'artifacts/imageio-native-progress.json':
    print('Preserving the newer original ImageIO/source-ABI checkpoint')
    raise SystemExit(0)

if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') == 'artifacts/mobilegestalt-progress.json':
    print('Preserving the newer MobileGestalt/source-dyld checkpoint')
    raise SystemExit(0)

read=lambda n:json.loads((root/n).read_text())
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
p=runpy.run_path(str(root/'scripts/container-persona-profile.py'))['profile']()
trace=p['source_libtrace'];selected=p['source_runtime']
assert trace['full_libtrace_source_build'] and trace['complete_source_files']==9
assert trace['original_exports_preserved']==142 and trace['source_exports']==145
assert p['source_kernel']['complete_source_files']==875
assert p['libtrace_source_override']==trace==p['log_hooks']['source_build']
for v in selected.values():assert digest(v['path'])==v['sha256']
for path,sha in {**trace['source_files'],**trace['source_headers']}.items():assert digest('vendor/darling/src/external/libtrace/'+path)==sha
for key in ['log_hooks','container_persona']:
 s=p[key];assert s['export_changes']['original_instructions_and_other_bytes_preserved'] and not s['export_changes']['provider_entire_namespace_reexported']
paths={
 'hooks':'artifacts/log-hooks-test.json',
 'persona':'artifacts/container-persona-test.json',
 'trace':'artifacts/libtrace-hooks-execution.json',
 'version':'artifacts/container-persona-xcode-version.json',
 'showsdks':'artifacts/container-persona-xcode-showsdks.json',
 'lsd':'artifacts/native-lsd-container-persona-probe.json'}
results={k:read(n) for k,n in paths.items()}
for name,r in results.items():
 assert r['source_runtime']==selected
 if 'log' in r:assert digest(r['log'])==r['log_sha256']
 for n,sha in r.get('logs',{}).items():assert digest(n)==sha
 if name!='showsdks':assert r['exit_status']==0
 if 'source_libtrace' in r:assert r['source_libtrace']==trace
 elif 'build' in r:assert r['build']==trace
 for key in ['log_hooks','container_persona','native_log_message','native_layer_context','native_layer_support']:
  if key in r:assert r[key]==p[key]
for name,source,binary in [
 ('hooks','fixtures/hello/log-hooks.m','artifacts/log-hooks'),
 ('persona','fixtures/hello/container-persona.c','artifacts/container-persona')]:
 assert digest(source)==results[name]['source_sha256'] and digest(binary)==results[name]['binary_sha256']
assert results['trace']['test_source_sha256']==digest('fixtures/hello/libtrace-source.m') and results['trace']['test_binary_sha256']==digest('artifacts/libtrace-hooks')
assert results['trace']['runtime_execution_verified'] and results['trace']['actual_ASL_stderr_record_text_verified']
hooks=(root/results['hooks']['log']).read_text()
counts=re.search(r'SOURCE_LOG_HOOK_REAL_SERIALIZED_EVENTS_LEVELS_OWNERSHIP_REENTRANCY_FAULT_AND_CONCURRENCY_OK checks=(\d+) calls=(\d+)',hooks);assert counts and int(counts[1])==1642 and int(counts[2])==419
assert 'HOOK_TEXT public macro -77' in hooks and hooks.count('HOOK_TEXT fault 42')==2
assert 'HOOK_TEXT No such file or directory' in hooks and 'HOOK_TEXT 你好 Linux' in hooks
assert results['persona']['runtime_execution_verified']
assert 'CONTAINER_PERSONA_POINTER_VARIABLE_ABI_ORIGINAL_VALUES_AND_REAL_SETTER_OK' in (root/results['persona']['log']).read_text()
assert results['lsd']['UTI_functional_execution_verified'] and not results['lsd']['frozen_trace_comparison']
assert 'NATIVE_UTI_TYPED_TAG_CONFORMANCE_AND_URL_EXTENSION_OK' in results['lsd']['diagnostic']
assert 'Error -43 registering path /System/Library/CoreServices/CoreTypes.bundle' not in results['lsd']['daemon_diagnostic']
assert 'Symbol not found:' not in results['lsd']['daemon_diagnostic']
for arg in p['command']:
 if arg.startswith(('DYLD_LIBRARY_PATH=','DYLD_FRAMEWORK_PATH=')):
  key,value=arg.split('=',1);assert results['lsd']['selected_job']['EnvironmentVariables'][key]==value
assert 'Xcode 26.6\nBuild version 17F113' in (root/results['version']['log']).read_text()
assert results['showsdks']['exit_status']==255
blocker='_MobileGestalt_copy_humanReadableProductVersionString_obj'
assert 'Symbol not found: '+blocker in (root/results['showsdks']['log']).read_text()
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
assert digest(original)==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
for mode in ['version','showsdks']:assert results[mode]['original_xcodebuild_sha256']==digest(original)
verification=read('artifacts/log-hooks-verification.json');assert verification['all_execution_regressions_passed'] and not verification['sdk_listing_succeeded']
for item in verification['checks']:assert digest(item['log'])==item['log_sha256']
analysis=read('artifacts/log-hooks-native-analysis.json')
assert digest(analysis['client'])==analysis['client_sha256'] and digest(analysis['log'])==analysis['log_sha256'] and digest(analysis['client_log'])==analysis['client_log_sha256']
assert analysis['native_initial_minimum_level']==17 and analysis['native_default_fault_callback_is_single_ret']
reference=read('vendor/webkit-oslog-reference/reference.json');assert digest('vendor/webkit-oslog-reference/OSLogSPI.h')==reference['sha256']
comparison='artifacts/native-lsd-container-persona-trace8-comparison-probe.json';c=read(comparison)
assert c['frozen_trace_comparison'] and c['exit_status']==0 and c['UTI_functional_execution_verified']
assert digest(c['source_libtrace']['library'])==c['source_libtrace']['library_sha256']
for n,sha in c['logs'].items():assert digest(n)==sha
failures=['artifacts/native-lsd-container-persona-startup-failure.json','artifacts/native-lsd-container-persona-startup-failure-2.json']
for path in failures:
 r=read(path);assert r['exit_status']!=0 and '"LastExitStatus" = 132' in r['diagnostic']
 for n,sha in r['logs'].items():assert digest(n)==sha
repo=root/'vendor/darling/src/external/libtrace'
tracked=['CMakeLists.txt','include/os/log_private.h','libsbuf/libsbuf.c','libsystem_trace/os_log.c','libsystem_trace/stubs.c','libsystem_trace/unpack_buffer.m'];added=['libsystem_trace/log_hooks.m']
patch=subprocess.check_output(['git','diff','--binary','--',*tracked],cwd=repo)
for path in added:
 assert subprocess.run(['git','ls-files','--error-unmatch',path],cwd=repo,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
 extra=subprocess.run(['git','diff','--no-index','--binary','--','/dev/null',path],cwd=repo,capture_output=True);assert extra.returncode==1;patch+=extra.stdout
patch_path='artifacts/darling-log-hooks-source.patch';temporary=root/(patch_path+'.pending');temporary.write_bytes(patch);temporary.replace(root/patch_path)
subprocess.run(['git','apply','--reverse','--check',str(root/patch_path)],cwd=repo,check=True)
evidence=list(paths.values())+['artifacts/libtrace-hooks-source-build.json','artifacts/log-hooks-stage.json','artifacts/container-persona-stage.json','artifacts/log-hooks-native-analysis.json','artifacts/mobilegestalt-version-native-analysis.json','artifacts/log-hooks-verification.json','vendor/webkit-oslog-reference/reference.json','vendor/webkit-oslog-reference/OSLogSPI.h',comparison,patch_path]+failures
scripts=['build-libtrace-source.py','log-enablement-profile.py','native-log-message-profile.py','stage-log-hooks.py','log-hooks-profile.py','analyze-log-hook-contracts.py','test-log-hooks.py','test-libtrace-source.py','verify-log-hooks-progress.py','container-persona-constants.c','stage-container-persona.py','container-persona-profile.py','test-container-persona.py','probe-native-layer-xcode.py','probe-native-lsd.py','debug-log-hooks-lsd.py','record-log-hooks-progress.py']
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),previous_report='artifacts/layer-log-progress.json',previous_goal_turn_classification='progress',current_goal_turn_classification='progress',
 evidence={n:digest(n) for n in evidence},scripts={'scripts/'+n:digest('scripts/'+n) for n in scripts},source_files={'vendor/darling/src/external/libtrace/'+n:digest('vendor/darling/src/external/libtrace/'+n) for n in tracked+added},
 selected_runtime=selected,source_libtrace=trace,original_xcodebuild_sha256=digest(original),
 native_message_type_getter_256_byte_values_verified=True,source_log_callback_assertions=int(counts[1]),source_log_callback_events=int(counts[2]),concurrent_events_verified=400,
 public_compiler_error_and_fault_macros_verified=True,source_serialized_public_and_redacted_private_text_verified=True,source_callback_copy_replace_recursion_and_fault_delivery_verified=True,
 native_persona_string_values_and_real_owned_query_setter_verified=True,original_LaunchServices_and_complete_current_UTI_fixture_verified=True,
 original_xcode_version_verified=True,sdk_listing_verified=False,full_xcode_build_ready=False,signing_ready=False,full_darling_rebuild=False,installed_as_default=False,
 current_blocker=blocker,
 implementation_form='Complete nine-file Darling source libtrace, real Block registration/exchange, native message getters and fault callback delivery from actual _os_log_impl events; compiler pointer records are serialized for the original formatter. Observation state initializes only after an observer is registered. Persona pointer variables preserve exact original C-string values and are consumed by the unchanged original CM query setter. Xcode and its framework binaries are unchanged; private named reexports preserve previous machine code.',
 regression_evidence='Unconditional callback TLS/locking introduced early original lsd failures (status 132). A preserved eight-file binary passed in the same runtime; a debugger-gated run also passed. Deferring observer-specific initialization until registration restored ungated original lsd/UTI; the final serial regression passes. The precise underlying early pthread/Framework interaction was not independently established.',
 limits=[
  'The tested callback ABI covers types, subsystem/category, format and real serialized public payload. Opaque trace-header fields, kernel trace IDs, stackshots, persistent logd delivery and all native format/plugin extensions are not implemented or verified.',
  'Private payload remains absent under the existing source privacy policy. This does not implement collection entitlements or native device log authorization. Fault text uses the existing source ASL decoder; full native formatting equivalence for every fault format is not claimed.',
  'Native minimum level starts at FAULT and only becomes more verbose. Previous copied Blocks can be chained by callers; null hook registration is rejected. Initializer/fork/signal safety and arbitrary observer exceptions have not been exhaustively verified.',
  'The first early-initialization failures are preserved, alongside the frozen old-binary comparison. Deferred callback activation is verified by the current regressions; no broader claim of a completely diagnosed Foundation/pthread initialization protocol is made.',
  'Persona string storage addresses differ from the original image. The actual original setter duplicates their identical bytes; no protected container record or positive daemon lookup is fabricated.',
  'Original MobileGestalt copy_humanReadableProductVersionString_obj returns an autoreleased Objective-C object despite copy in its C name. Its source backend is still missing and is the current SDK loader blocker.',
  'Earlier CoreGraphics window/GPU, metadata, container policy and LaunchServices translocation limits remain. Default runtime is unchanged; no unified full Darling rebuild or full project/archive/sign/export success exists.'])
destination='artifacts/log-hooks-progress.json';temporary=root/(destination+'.pending');temporary.write_text(json.dumps(record,indent=2)+'\n');temporary.replace(root/destination)
state=read('artifacts/current-work-state.json')
state.update(updated_at=record['checked_at'],primary_report=destination,goal_status='active',complete=False,active_build=dict(task='source-log-hooks-native-persona-and-restored-LaunchServices',running=False,report=destination),latest_selected_runtime=selected,latest_implementation_form=record['implementation_form'],latest_xcode_loader_blocker=blocker,latest_staged_coreml_and_metal_blocker=blocker)
state['next_work']=list(dict.fromkeys([
 'Implement the actual MobileGestalt human-readable product-version property backend used by original XCTHarness. Inspect the property callback and guest SystemVersion metadata, including ProductVersionExtra; preserve the observed autoreleased object ABI rather than inferring +1 ownership from the copy name.',
 'Continue unchanged genuine xcodebuild -showsdks after MobileGestalt; then validate original project build/archive/sign/export and CocoaPods/Unity-generated inputs. Exercise original XCTest logging consumers after the remaining loader requirements are satisfied.',
]+[s for s in state['next_work'] if not s.startswith(('Implement real source logging hooks needed','Continue genuine unchanged xcodebuild -showsdks after logging integration'))]))
state['last_verification']=list(dict.fromkeys(state['last_verification']+['Nine-file source logging provider passes 1642 callback assertions, 419 observed events including 400 concurrent events, all 256 getter byte values, real public error/fault macros and previous 21-case ASL regression. Actual persona values work with original owned query setters. After deferring callback initialization, final ungated original lsd/UTI and xcodebuild -version pass; SDK listing fails on MobileGestalt human-readable version. Full goal remains active.']))
state['latest_validation_reports']=list(dict.fromkeys(state['latest_validation_reports']+evidence+[destination]))
state.setdefault('source_components',{}).update(libtrace='artifacts/libtrace-hooks-source-build.json',log_hooks='artifacts/log-hooks-stage.json',container_persona='artifacts/container-persona-stage.json',log_hooks_progress=destination)
temporary=root/'artifacts/current-work-state.json.pending';temporary.write_text(json.dumps(state,indent=2)+'\n');temporary.replace(root/'artifacts/current-work-state.json')
print('Recorded real source callbacks, persona values and restored original UTI; full Xcode goal remains active')
