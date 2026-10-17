#!/usr/bin/env python3
"""Publish real source selector lookup, coherent Foundation, and genuine SDK listing."""

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
read=lambda n:json.loads((root/n).read_text());digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
p=runpy.run_path(str(root/'scripts/foundation-coherent-profile.py'))['profile']();objc=p['source_objc'];selector=p['source_selector'];foundation=p['foundation_coherent'];selected=p['source_runtime']
assert objc['full_objc_source_build'] and objc['complete_source_files']==43 and objc['source_export_count']==771 and not objc['missing_original_exports']
for n,sha in objc['source_files'].items():assert digest('vendor/darling/src/external/objc4/runtime/'+n)==sha
for n,sha in objc['build_inputs'].items():assert digest(n)==sha
assert digest(objc['library'])==objc['library_sha256'] and selector['old_guard_source_sha256']==digest('scripts/objc-selector-lookup.c')
assert selector['export_changes']['original_instructions_and_other_bytes_preserved'] and not selector['export_changes']['provider_entire_namespace_reexported']
for v in selected.values():assert digest(v['path'])==v['sha256']
paths={'selector':'artifacts/objc-selector-source-test.json','float':'artifacts/foundation-coherent-test.json','lsd':'artifacts/native-lsd-foundation-coherent-probe.json','version':'artifacts/foundation-coherent-xcode-version.json','unmanaged_sdk':'artifacts/foundation-coherent-xcode-showsdks.json','sdk':'artifacts/foundation-coherent-managed-xcode-showsdks.json','build':'artifacts/foundation-coherent-managed-xcode-build.json'}
results={k:read(n) for k,n in paths.items()}
for name,r in results.items():
 assert r['source_runtime']==selected and r['source_objc']==objc and r['source_selector']==selector
 if name!='selector':assert r['foundation_coherent']==foundation
 if 'log' in r:assert digest(r['log'])==r['log_sha256']
 for n,sha in r.get('logs',{}).items():assert digest(n)==sha
 if name in ['lsd','version','sdk']:assert r['exit_status']==0
for name in ['selector','float']:
 r=results[name];assert r['runtime_execution_verified']
 for c in r['checks']:assert c['exit_status']==0 and c['verified'] and c['log_sha256']==digest(c['log'])
assert len(results['selector']['checks'])==5
for n,sha in {**results['selector']['sources'],**results['selector']['binaries']}.items():assert digest(n)==sha
assert results['float']['source_sha256']==digest('fixtures/hello/constant-float-number.m') and results['float']['binary_sha256']==digest('artifacts/constant-float-native-smoke')
assert len(results['float']['checks'])==2 and 'APPLE_CLANG_CONSTANT_FLOAT_LAYOUT_BITS_CF_BRIDGE_EQUALITY_HASH_COPY_OK' in (root/results['float']['checks'][-1]['log']).read_text()
assert foundation['shim']['exports']==2
assert foundation['float_class']['export_changes']['original_instructions_and_other_bytes_preserved'] and not foundation['float_class']['export_changes']['provider_entire_namespace_reexported']
assert 'Xcode 26.6\nBuild version 17F113' in (root/results['version']['log']).read_text()
lsd=results['lsd'];assert lsd['UTI_functional_execution_verified'] and not lsd['frozen_trace_comparison'] and 'NATIVE_UTI_TYPED_TAG_CONFORMANCE_AND_URL_EXTENSION_OK' in lsd['diagnostic']
for arg in p['command']:
 if arg.startswith(('DYLD_LIBRARY_PATH=','DYLD_FRAMEWORK_PATH=')):
  k,v=arg.split('=',1);assert lsd['selected_job']['EnvironmentVariables'][k]==v
sdk=results['sdk'];text=(root/sdk['log']).read_text();assert sdk['UTI_preflight_verified'] and 'MANAGED_XCODE_ORIGINAL_STATUS 0' in text
for value in ['DriverKit SDKs:','iOS SDKs:','iOS Simulator SDKs:','macOS SDKs:','tvOS SDKs:','visionOS SDKs:','watchOS SDKs:','-sdk iphoneos26.5','-sdk macosx26.5']:assert value in text
assert 'Objective-C selector backend UUID/code/layout guard rejected' not in text and 'is implemented in both' not in text
assert '"LastExitStatus" = 132' in text
for name in ['sdk','build']:
 r=results[name];assert digest(r['script'])==r['script_sha256'];body=(root/r['script']).read_text();assert '/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild "$@"' in body
 for job in r['jobs']:assert digest(job['path'])==job['sha256']
assert results['build']['exit_status']==1 and results['build']['UTI_preflight_verified']
assert '** BUILD SUCCEEDED **' not in (root/results['build']['log']).read_text()
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild';assert digest(original)==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
for name in ['version','sdk','build','unmanaged_sdk']:assert results[name]['original_xcodebuild_sha256']==digest(original)
daemon_log='logs/foundation-coherent-managed-xcode-showsdks-lsd.log';daemon=(root/daemon_log).read_text();assert "attempt to post distributed notification" in daemon and 'thwarted by sandboxing' in daemon
repo=root/'vendor/darling/src/external/objc4';files=['runtime/NSObject.mm','runtime/objc-object.h','runtime/objc-private.h','runtime/objc-sel.mm','runtime/objc.h','unexported_symbols'];patch=subprocess.check_output(['git','diff','--binary','--',*files],cwd=repo);assert patch
out='artifacts/darling-objc-selector-source.patch';pending=root/(out+'.pending');pending.write_bytes(patch);pending.replace(root/out);subprocess.run(['git','apply','--reverse','--check',str(root/out)],cwd=repo,check=True)
evidence=list(paths.values())+[out,'artifacts/objc-selector-source-build.json','artifacts/objc-selector-source-stage.json','artifacts/foundation-coherent-stage.json','artifacts/foundation-coherent-next-services-analysis.json','config/cache-image-pins.json','logs/foundation-coherent-xcode-stacks.gdb.log','logs/foundation-coherent-xcode-stacks.maps.log','logs/foundation-coherent-xcode-stacks.annotated.log',daemon_log,'logs/foundation-coherent-managed-xcode-showsdks-dirhelper.log','logs/foundation-coherent-managed-xcode-build-lsd.log','logs/foundation-coherent-managed-xcode-build-dirhelper.log']
scripts=['build-objc-source.py','stage-objc-selector-source.py','objc-selector-source-profile.py','test-objc-selector-source.py','stage-foundation-coherent.py','foundation-coherent-profile.py','test-foundation-coherent.py','capture-darling-stacks.py','probe-xcode-managed-services.py','probe-native-layer-xcode.py','probe-native-lsd.py','record-foundation-coherent-progress.py']
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),previous_report='artifacts/fsevents-flush-progress.json',previous_goal_turn_classification='progress',current_goal_turn_classification='progress',source_runtime=selected,source_objc=objc,source_selector=selector,foundation_coherent=foundation,evidence={n:digest(n) for n in evidence},scripts={'scripts/'+n:digest('scripts/'+n) for n in scripts},sdk_listing_succeeded=True,sdk_listing_exit_status=0,launchservices_stable_after_sdk=False,project_build_succeeded=False,project_build_exit_status=1,original_xcode_version_verified=True,default_launcher_switched=False,goal_status='active',complete=False,full_xcode_build_ready=False,signing_ready=False,
 implementation_form='Complete 43-file source objc4 with actual sel_lookUpByName over its builtin selector search and selLock-protected registry; unknown names are not interned. A private helper explicitly reexports that API, preserving the old guarded implementation outside this profile. Native libswiftFoundation forwarding image and native NSConstantFloatNumber replace duplicate compatibility definitions in the private composition. Original lsd/dirhelper jobs are loaded in the same isolated session, then the unchanged original xcodebuild command is executed with its original arguments. No SDK list is generated or substituted by the launcher.',
 remaining_limits=[
 'Genuine SDK listing succeeds, but original lsd exits 132 after registration/distributed-notification posting. CoreFoundation reports a distributed notification service/sandbox failure; native distnoted service names, lifecycle and identity require implementation/validation. Standalone read-only UTI success does not establish daemon stability after original Xcode use.',
 'The preserved minimal XcodeSmoke project build exits 1 before a successful build or managed status footer. Its exact exit path is not yet diagnosed. Darwin quotactl 165 returns ENOSYS and is also printed in successful SDK listing, so it is not established as the build-failure cause.',
 'Missing original Info.plist resources in some staged OS frameworks still cause original DVT plugin-scan warnings. SDK listing includes duplicate macOS 26.5 entries; platform enumeration/canonicalization is not exhaustively validated.',
 'Without original LS service startup in the same session, original Xcode waits for an NSXPC synchronous reply. Captured actual stacks are retained; all future CI integration must preserve real service startup/errors.',
 'The actual source selector and float/class behavior tests pass, but broad Objective-C/Foundation compatibility is not implied. The old selector guard is unchanged and should still reject a mismatched runtime if explicitly selected.',
 'Earlier complex timed-run-loop, ImageIO image-provider/decode, device identity, metadata, sandbox policy, certificate trust, signing/export, graphics/window and XPC limits remain. No full Unity/CocoaPods project build/archive/sign/export has succeeded. The default launcher is unchanged.'])
destination='artifacts/foundation-coherent-progress.json';pending=root/(destination+'.pending');pending.write_text(json.dumps(record,indent=2)+'\n');pending.replace(root/destination)
state=read('artifacts/current-work-state.json');state.update(updated_at=record['checked_at'],primary_report=destination,goal_status='active',complete=False,latest_selected_runtime=selected,latest_implementation_form=record['implementation_form'],latest_xcode_loader_blocker=None,latest_xcode_runtime_failure='Original project build exits 1; LS distributed-notification posting exits 132 after SDK listing',latest_xcode_failure_kind='project_build_and_service_runtime',latest_staged_coreml_and_metal_blocker='Original project-build / service runtime failure',latest_sdk_listing_succeeded=True,active_build=dict(task='source-selector-native-Foundation-and-original-SDK-listing',running=False,report=destination))
state['next_work']=list(dict.fromkeys([
 'Resolve actual distributed-notification service startup/identity/protocol for native LaunchServices registration. Original SDK listing exits 0, but lsd then exits 132 while posting a distributed notification. Inspect genuine distnoted agent/daemon and correct service lookup; do not suppress CoreFoundation sandbox/service errors.',
 'Trace the exact exit path of unchanged XcodeSmoke project build under the paired original services. It currently exits 1 before a build-success or managed status footer. Check build-service startup and actual original command behavior; quotactl ENOSYS alone is not a proven cause.',
 'Integrate the verified current source/native profile and original service startup into a reproducible private CI entry while preserving original xcodebuild arguments and project files, after actual build/service behavior is validated. Then continue Unity-exported/CocoaPods build/archive/native signing/export.',
]+[s for s in state['next_work'] if not s.startswith(('Implement sel_lookUpByName','Make native Foundation initialization coherent'))]))
state['last_verification']=list(dict.fromkeys(state['last_verification']+['Complete 43-file source objc runtime now exports actual non-registering sel_lookUpByName. Direct and helper lookup pass 12000 concurrent registered names per session, unknown/UTF8/identity checks, class enumeration and native signature/tagged-object regressions. The actual current libswiftFoundation forwarding image and native float class remove duplicate definitions; original Apple clang float literal ABI/CF/hash/copy tests pass. With original lsd/dirhelper in the same Linux session, unchanged xcodebuild -showsdks exits 0 and lists real SDKs. After listing, lsd exits 132 on distributed notification posting; minimal project build exits 1. Full goal remains active.']))
state['latest_validation_reports']=list(dict.fromkeys(state['latest_validation_reports']+evidence+[destination]));state['source_components'].update(objc='artifacts/objc-selector-source-build.json',objc_selector='artifacts/objc-selector-source-stage.json',objc_selector_execution='artifacts/objc-selector-source-test.json',foundation_coherent='artifacts/foundation-coherent-stage.json',foundation_coherent_execution='artifacts/foundation-coherent-test.json',managed_xcode_sdk='artifacts/foundation-coherent-managed-xcode-showsdks.json',managed_xcode_build='artifacts/foundation-coherent-managed-xcode-build.json',foundation_coherent_progress=destination)
pending=root/'artifacts/current-work-state.json.pending';pending.write_text(json.dumps(state,indent=2)+'\n');pending.replace(root/'artifacts/current-work-state.json');print('Recorded genuine SDK listing success and actual service/project-build failures; full goal remains active')
