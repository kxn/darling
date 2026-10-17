#!/usr/bin/env python3
"""Record source query behavior and the original project's next observed waits."""
from pathlib import Path
from datetime import datetime,timezone
import ast,fcntl,hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
if (root/'artifacts/icu-signal-progress.json').exists():
 print('Preserving the newer original ICU and fatal signal checkpoint');raise SystemExit(0)
read=lambda n:json.loads((root/n).read_text());digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
resolve=runpy.run_path(str(root/'scripts/resolve-evidence-history.py'))['resolve'];evidence={}
def add(n,sha=None):
 n=resolve(str(n),sha) if sha else str(n);evidence[n]=digest(n)
 if sha:assert evidence[n]==sha,n
def walk(d):
 if isinstance(d,list):
  for x in d:walk(x)
 elif isinstance(d,dict):
  for k,v in d.items():
   if isinstance(v,str) and isinstance(d.get(k+'_sha256'),str) and (root/v).is_file():add(v,d[k+'_sha256'])
   if k=='sha256':
    for field in ['source','path','file']:
     if field+'_sha256' not in d and isinstance(d.get(field),str) and (root/d[field]).is_file():add(d[field],v)
   if isinstance(v,str) and re.fullmatch('[a-f0-9]{64}',v) and (root/k).is_file():add(k,v)
   if isinstance(v,(dict,list)):walk(v)
def report(n):
 d=read(n);add(n);walk(d);return d
with (root/'runtime/session.lock').open('a') as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
previous=report('artifacts/xpc-activation-materialize-progress.json')
build=report('artifacts/mobileasset-query-build.json');assert build['complete_source_files']==15
native=report('artifacts/mobileasset-query-native-test.json');assert native['verified'] and native['checks']==1823
regression=report('artifacts/mobileasset-query-regressions.json');assert regression['verified'] and len(regression['results'])==2
metadata=report('artifacts/mobileasset-query-native-analysis.json');protocol=report('artifacts/mobileasset-query-protocol-native.json')
methods={m['selector']:m['types'] for m in metadata['classes'][0]['methods']}
assert methods['queryMetaData:']=='v24@0:8@?16' and methods['queryMetaDataWithError:']=='v24@0:8@?16'
projects=[]
for path in sorted((root/'artifacts').glob('xcode-service-runtime-mobileasset-query-diagnostic-build-*.json')):
 n=str(path.relative_to(root));d=report(n);text=(root/d['log']).read_text()
 assert d['UTI_preflight_verified'] and not d['legacy_volume_API_prewarm_used'] and not d['xcode_process_returned']
 assert 'Failed querying assets for assetType (com.apple.MobileAsset.MetalToolchain)' in text
 assert 'leaked its continuation' not in text and 'Stub called: initWithType: in MAAssetQuery' not in text
 assert not re.search(r'^CompileC |^SwiftCompile ',text,re.M)
 projects.append(dict(report=n,sha256=digest(n),exit_status=d['exit_status'],xcode_process_returned=False,UTI_preflight_verified=True))
assert len(projects)==2
sym=report('artifacts/mobileasset-query-xcode-live-symbolication.json');stacks=(root/sym['output']).read_text()
for marker in ['+[DVTKVOConditionValidator waitForCondition:', '_resolveInputOptionsWithTimingSection:', 'deriveMetal', 'waitUntilExit', 'ucsp_client_verifyPrivileged2', '___loadValidCoreSimulatorService_block_invoke_2']:
 assert marker in stacks,marker
xcode={}
for mode in ['version','showsdks']:
 paths=list((root/'artifacts').glob('xcode-service-runtime-mobileasset-query-'+mode+'-*.json'));assert len(paths)==1
 n=str(paths[0].relative_to(root));d=report(n);assert d['exit_status']==0 and d['UTI_preflight_verified'] and d['xcode_process_returned']
 xcode[mode]=dict(report=n,sha256=digest(n),exit_status=0)
for n in ['scripts/analyze-mobileasset-query-protocol.py','scripts/build-mobileasset-query-source.py','scripts/mobileasset-query-runtime-profile.py','scripts/test-mobileasset-query.py','scripts/test-mobileasset-query-regressions.py','scripts/probe-mobileasset-query-xcode-stacks.py','scripts/symbolicate-darling-stack.py','scripts/probe-xcode-service-runtime.py','scripts/cryptex-native-profile.py','scripts/record-mobileasset-query-progress.py','scripts/resolve-evidence-history.py','fixtures/hello/mobileasset-query.m','artifacts/mobileasset-query-initial-history/manifest.json','logs/mobileasset-query-source-build.log','logs/mobileasset-query-xcode-early.gdb.log','logs/mobileasset-query-xcode-early.maps.log','logs/mobileasset-query-cfprefsd-live.gdb.log','logs/mobileasset-query-cfprefsd-live.maps.log','logs/mobileasset-query-xcode-stacks-launch.log']:
 add(n)
 if n.endswith('.py'):ast.parse((root/n).read_text())
source='vendor/darling/src/private-frameworks/MobileAsset';files=['src/MAAssetQuery.m','include/MobileAsset/MAAssetQuery.h','src/MAAsset.m','include/MobileAsset/MAAsset.h'];patch='artifacts/darling-mobileasset-query-source.patch'
(root/patch).write_bytes(subprocess.check_output(['git','-C',str(root/'vendor/darling'),'diff','HEAD','--',*[str(Path(source).relative_to('vendor/darling')/n) for n in files]]))
subprocess.run(['git','-C',str(root/'vendor/darling'),'apply','--reverse','--check',str(root/patch)],check=True);add(patch)
p=runpy.run_path(str(root/'scripts/mobileasset-query-runtime-profile.py'))['profile']()
d=dict(checked_at=datetime.now(timezone.utc).isoformat(),goal_status='active',complete=False,full_xcode_build_ready=False,signing_ready=False,default_entry_promoted=False,
 previous_goal_turn_classification='progress',current_goal_turn_classification='progress',source_runtime=p['source_runtime'],source_mobileasset_query=build,
 source_framework_files=15,source_framework_exports_preserved=build['original_exports_preserved'],native_query_checks=1823,actual_query_test_peer_requests=48,
 native_async_concurrent_threads=4,native_concurrent_async_queries=32,native_detached_query_callbacks=8,native_absent_service_returns_real_XPC_error=True,
 source_query_params_keyed_archive_and_native_request_schema_verified=True,source_query_reply_secure_results_and_metadata_verified=True,
 source_query_async_callback_ABI_verified=True,source_query_async_uses_sync_wire_on_dispatch_worker=True,full_native_async_task_manager_implemented=False,
 existing_Pallas_transport_regressions_pass=True,original_Xcode_MobileAsset_Swift_continuation_leak_resolved=True,
 original_MobileAsset_daemon_running=False,local_asset_catalog_daemon_implemented=False,asset_download_implemented=False,asset_getLocalFilePath_implemented=False,
 original_xcode_regressions=xcode,original_project_attempts=projects,latest_original_project=next(x for x in projects if '17adccbdf70e' in x['report']),
 current_observed_failure='Original Xcode completes its real MobileAsset failure callback. The original project remains in input-option condition waiting; live background stacks show SwiftPM deriveMetalToolchainPath waiting for subprocess exit, CoreSimulator service loading and SecurityServer verifyPrivileged2 Mach IPC. The directly causal wait is not yet established; no CompileC/SwiftCompile was observed.',
 original_Xcode_main_wait='DVTKVOConditionValidator waitForCondition during _resolveInputOptionsWithTimingSection',
 actual_project_compilation_started=False,diagnostic_build_uses_explicit_permissive_coreservices_policy=True,strict_Sandbox_enforcement_verified=False,
 evidence=evidence,next_work=[
 'Capture the live subprocess commands, pipes and process trees while original SwiftPM derives the Metal toolchain; trace the concrete child wait and real CoreSimulator/securityd bootstrap jobs. Establish which unfinished condition blocks original input-option resolution before changing service behavior.',
 'Implement real daemon/catalog/access/download behavior as needed; the source MobileAsset query client is not an asset provider. Complete native asynchronous task/retry management if required; current public async ABI uses a dispatch worker and genuine synchronous wire requests.',
 'Continue unchanged original project into actual compile/link, Unity/CocoaPods, archive, signing and export. Restrictive Sandbox, startup volumes, actual RunningBoard monitoring and previously documented gaps remain incomplete.'
 ])
(root/'artifacts/mobileasset-query-progress.json').write_text(json.dumps(d,indent=2)+'\n');print('Recorded',len(evidence),'hashes; real source query/callback fixed; original input-option dependency waits remain')
