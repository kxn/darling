#!/usr/bin/env python3
"""Verify source crash fixes and publish the actual remaining Xcode failures."""

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
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
read=lambda n:json.loads((root/n).read_text())
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
p=runpy.run_path(str(root/'scripts/log-pack-profile.py'))['profile']()
trace=p['source_libtrace'];events=p['source_fsevents']
assert trace['full_libtrace_source_build'] and trace['complete_source_files']==9
assert trace['original_exports_preserved']==142 and trace['source_exports']==145
assert events['full_FSEvents_source_component_build'] and events['complete_source_files']==2
assert events['original_exports_preserved']==29 and events['source_exports']==57
for build,base in [(trace,'vendor/darling/src/external/libtrace/')]:
    assert digest(build['library'])==build['library_sha256']
    for name,sha in {**build['source_files'],**build['source_headers']}.items():assert digest(base+name)==sha
assert digest(events['library'])==events['library_sha256']
for name,sha in {**events['sources'],**events['headers']}.items():assert digest(name)==sha
for item in p['source_runtime'].values():assert digest(item['path'])==item['sha256']
paths={'pack':'artifacts/log-pack-test.json','events':'artifacts/fsevents-heap-test.json','build':'artifacts/xcode-service-runtime-pack-build.json','sdk':'artifacts/xcode-service-runtime-pack-showsdks.json','version_and_failed_daemon':'artifacts/xcode-service-runtime-pack-daemon-version.json'}
results={name:read(path) for name,path in paths.items()}
for name,result in results.items():
    for key in ['source_runtime','source_objc','source_selector','foundation_coherent','source_libtrace','source_fsevents']:
        assert result[key]==p[key],(name,key)
    if 'log' in result:assert digest(result['log'])==result['log_sha256']
for name in ['pack','events']:
    result=results[name];assert result['runtime_execution_verified'] and len(result['checks'])==2
    for check in result['checks']:
        assert check['verified'] and check['exit_status']==0 and digest(check['log'])==check['log_sha256']
        if 'source' in check:assert digest(check['source'])==check['source_sha256']
        if 'binary' in check:assert digest(check['binary'])==check['binary_sha256']
pack=results['pack'];assert digest(pack['source'])==pack['source_sha256'] and digest(pack['binary'])==pack['binary_sha256']
assert digest(pack['original'])==pack['original_sha256']
assert digest('fixtures/hello/log-hooks.m')==pack['hook_source_sha256']
assert 'checks=269 calls=8' in (root/pack['checks'][0]['log']).read_text()
assert 'checks=1642 calls=419' in (root/pack['checks'][1]['log']).read_text()
assert 'events=2 stack=65536' in (root/results['events']['checks'][0]['log']).read_text()
assert 'checks=88' in (root/results['events']['checks'][1]['log']).read_text()
sdk=results['sdk'];sdk_text=(root/sdk['log']).read_text()
assert sdk['exit_status']==0 and sdk['UTI_preflight_verified'] and 'SERVICE_RUNTIME_XCODE_STATUS 0' in sdk_text
for value in ['DriverKit SDKs:','iOS SDKs:','macOS SDKs:','tvOS SDKs:','visionOS SDKs:','watchOS SDKs:']:assert value in sdk_text
assert '"LastExitStatus" = 132;' in sdk_text
version=results['version_and_failed_daemon'];version_text=(root/version['log']).read_text()
assert version['exit_status']==0 and version['UTI_preflight_verified']
assert 'Xcode 26.6\nBuild version 17F113' in version_text
assert 'uid=241(_distnote) gid=241(_distnote)' in version_text and '"LastExitStatus" = 134;' in version_text
assert 'failed to retrieve group list' in version_text
assert '_sandbox_check_by_reference' in (root/'logs/xcode-service-runtime-pack-daemon-version-distnoted-daemon.log').read_text()
for name in ['passwd','master.passwd','group']:assert '_distnote:' not in (root/'runtime/state/prefix/private/etc'/name).read_text()
build=results['build'];build_text=(root/build['log']).read_text()
assert build['exit_status']==70 and build['UTI_preflight_verified'] and 'SERVICE_RUNTIME_XCODE_STATUS 70' in build_text
assert '/Library/Developer/PrivateFrameworks/DVTDownloads.framework/Versions/A/DVTDownloads' in build_text
assert '** BUILD SUCCEEDED **' not in build_text
for name in ['build','sdk','version_and_failed_daemon']:
    result=results[name]
    assert '/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild "$@"' in (root/result['script']).read_text()
    assert digest(result['script'])==result['script_sha256']
    for job in result['jobs']:assert digest(job['path'])==job['sha256']
    assert 'is implemented in both' not in (root/result['log']).read_text()
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
assert digest(original)==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')==build['original_xcodebuild_sha256']
resource=read('artifacts/xcode-system-resources-stage.json')
assert not resource['prefix_links_published'] and not resource['run_first_launch_completed']
assert not resource['postinstall_executed'] and not resource['installer_receipts_created']
assert len(resource['payload_files'])==1828
for name,sha in resource['payload_files'].items():assert digest(name)==sha
for name,target in resource['prefix_links'].items():assert not (root/name).is_symlink() and not (root/name).exists()
experiment=read('artifacts/xcode-service-runtime-resources-build.json')
assert experiment['exit_status']==255 and 'Library not loaded: /usr/lib/libmdns.dylib' in (root/experiment['log']).read_text()
assert digest(experiment['log'])==experiment['log_sha256']
for stem in ['xcode-project-crash','xcode-project-pack-crash']:
    assert 'received signal SIGSEGV' in (root/('logs/'+stem+'.gdb.log')).read_text()
assert 'SystemConfiguration fileoff=0x8eb0 _get_sysctl_val+0xe8' in (root/'logs/xcode-project-crash.symbols.log').read_text()
assert '-[FSEventsImpl _readEvents]+0x9f' in (root/'logs/xcode-project-pack-crash.symbols.log').read_text()
patches=[]
for repo,output,include in [
    ('vendor/darling/src/external/libtrace','artifacts/darling-libtrace-pack-source.patch',None),
    ('vendor/darling/src/frameworks/CoreServices','artifacts/darling-fsevents-heap-source.patch',['src/FSEvents','include/FSEvents'])]:
    command=['git','-C',repo,'diff','--binary','HEAD','--',*(include or [])]
    patch=subprocess.check_output(command,cwd=root)
    if include is None:
        untracked=subprocess.run(['git','diff','--no-index','--binary','--','/dev/null','libsystem_trace/log_hooks.m'],cwd=root/repo,capture_output=True)
        assert untracked.returncode==1;patch+=untracked.stdout
    (root/output).write_bytes(patch)
    subprocess.run(['git','apply','--reverse','--check',str(root/output)],cwd=root/repo,check=True)
    patches.append(output)
evidence=list(paths.values())+patches+['artifacts/libtrace-pack-source-build.json','artifacts/fsevents-heap-source-build.json','artifacts/log-pack-next-runtime-analysis.json','artifacts/xcode-system-resources-stage.json','artifacts/xcode-system-resources-extraction.json','artifacts/xcode-service-runtime-resources-build.json','artifacts/xcode-service-runtime-trace-invalidated.json']
for stem in ['xcode-project-crash','xcode-project-pack-crash']:
    evidence.extend('logs/'+stem+suffix for suffix in ['.gdb.log','.maps.log','.symbols.log'])
for result in [*results.values(),experiment]:
    if 'log' in result:evidence.append(result['log'])
    for job in result.get('jobs',[]):evidence.append(job['job']['StandardOutPath'].removeprefix('/Volumes/SystemRoot/workspace/'))
scripts=['scripts/record-log-pack-progress.py','scripts/build-libtrace-source.py','scripts/build-fsevents-source.py','scripts/log-hooks-profile.py','scripts/fsevents-flush-profile.py','scripts/log-pack-profile.py','scripts/probe-xcode-service-runtime.py','scripts/test-log-pack.py','scripts/test-fsevents-heap.py','scripts/runtime-ns.sh','scripts/stage-xcode-system-resources.py','scripts/xcode-system-resources-profile.py','scripts/extract-xip.py','scripts/debug-xcode-project-crash.py','scripts/capture-darling-stacks.py','scripts/annotate-darling-capture.py']
record={'checked_at':datetime.now(timezone.utc).isoformat(),'previous_report':'artifacts/foundation-coherent-progress.json','previous_goal_turn_classification':'no progress','previous_goal_turn_explanation':'The intervening user question received a status-only answer. This continuation revalidated files and execution, fixed two observed source defects and gathered new original Xcode failures.','current_goal_turn_classification':'progress','source_runtime':p['source_runtime'],'source_libtrace':trace,'source_fsevents':events,'original_xcodebuild_sha256':digest(original),'sdk_listing_succeeded':True,'sdk_listing_exit_status':0,'original_xcode_version_verified':True,'project_build_succeeded':False,'project_build_exit_status':70,'project_build_blocker':'Required original DVTDownloads framework from the bundled system-resource package is not installed in the active profile','resource_dependency_blocker':'Original CoreDevice from the bundled package requires missing libmdns; package prefix links were withdrawn after the experiment','launchservices_stable_after_sdk':False,'distnoted_protocol_execution_verified':False,'distnoted_loader_blocker':'_sandbox_check_by_reference','default_launcher_switched':False,'full_xcode_build_ready':False,'signing_ready':False,'goal_status':'active','complete':False,'implementation_form':'Direct Darling source changes: modern Intel log-pack layout/fill/compiler encoding and actual ASL/hook/fault delivery, plus heap-backed inotify reads with exception cleanup. Complete 9-file libtrace and 2-file FSEvents components are rebuilt; original Xcode and its project/arguments are preserved. Native system-resource payloads are staged but unpublished pending real dependency closure. Account overrides mount onto the live guest overlay in a private mount namespace; no shared account data is changed.','evidence':{name:digest(name) for name in dict.fromkeys(evidence)},'scripts':{name:digest(name) for name in scripts},'limits':['The original project now returns a proper plugin-loading error 70 after the two captured crashes were fixed. No successful xcodebuild project/archive/sign/export is proven.','Eight valid pack allocation sizes were compared with original Intel leaf machine code; this does not establish the full native unified logging, composition or daemon protocols. Source logging uses the real existing ASL output backend.','The small-stack and 88-check event tests do not prove persistent/global event IDs, recursive coverage, full flags or the earlier complex timed CFRunLoop timeout defect.','Original distnoted remains unavailable: the correct named uid/gid is visible, but supplementary-group enumeration fails and missing sandbox-reference APIs abort the daemon. Identity mapping is not a security-isolation proof.','The XcodeSystemResources payload has verified archive checksums, but installer CMS trust, postinstall/device-image updates and first-launch completion are not verified. No installer receipt or completion state was fabricated.','SDK listing still has duplicate macOS rows and OS framework Info.plist warnings. lsd exits 132 after distributed notification posting; read-only UTI preflight and SDK command success do not prove service stability.','Earlier graphics, CF timing, filesystem metadata, sandbox policy, XPC identity/authorization and certificate trust limitations remain.']}
destination='artifacts/log-pack-progress.json';pending=root/(destination+'.pending');pending.write_text(json.dumps(record,indent=2)+'\n');pending.replace(root/destination)
state=read('artifacts/current-work-state.json');state.update(updated_at=record['checked_at'],primary_report=destination,goal_status='active',complete=False,latest_selected_runtime=p['source_runtime'],latest_implementation_form=record['implementation_form'],latest_xcode_loader_blocker=record['project_build_blocker'],latest_xcode_runtime_failure='Original project returns plugin-load error 70; original distnoted aborts on missing sandbox-reference API; lsd still exits 132 after SDK listing',latest_xcode_failure_kind='original_plugin_dependency_and_notification_service',latest_staged_coreml_and_metal_blocker='Original Xcode system-resource package dependency closure is incomplete',latest_sdk_listing_succeeded=True,active_build={'task':'source-log-pack-and-FSEvents-stack-fixes','running':False,'report':destination})
state['next_work']=read('artifacts/log-pack-next-runtime-analysis.json')['next_work']+[item for item in state['next_work'] if not item.startswith(('Trace the exact exit path of unchanged XcodeSmoke','Resolve actual distributed-notification service startup'))]
state['last_verification'].append('Source Intel log-pack size/fill matches original leaf code for eight valid sizes; 269 ABI/delivery checks and 1642 existing log-hook checks pass. A captured real FSEvents guard-page fault is fixed with heap storage; public start/read/sync-flush on a 65536-byte thread stack and all 88 flush checks pass. Original Xcode version/SDK listing remain exit 0; preserved project now returns actual plugin error 70. Original system-resource package exposes missing libmdns and remains unpublished; distnoted needs real sandbox-reference APIs. Full build/sign/export remains incomplete.')
state['latest_validation_reports']=list(dict.fromkeys(state['latest_validation_reports']+list(dict.fromkeys(evidence))+[destination]))
state['source_components'].update(libtrace_pack='artifacts/libtrace-pack-source-build.json',libtrace_pack_execution='artifacts/log-pack-test.json',fsevents_heap='artifacts/fsevents-heap-source-build.json',fsevents_heap_execution='artifacts/fsevents-heap-test.json',log_pack_progress=destination,xcode_system_resources_payload='artifacts/xcode-system-resources-stage.json')
pending=root/'artifacts/current-work-state.json.pending';pending.write_text(json.dumps(state,indent=2)+'\n');pending.replace(root/'artifacts/current-work-state.json')
print('Recorded source crash fixes and actual original Xcode dependency/service failures; full goal remains active')
