#!/usr/bin/env python3
"""Record real XPC failure delivery and native file-access policy progress."""
from pathlib import Path
from datetime import datetime,timezone
import ast,difflib,fcntl,hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
if (root/'artifacts/mobileasset-query-progress.json').exists():
 print('Preserving the newer source MobileAsset query checkpoint');raise SystemExit(0)
read=lambda n:json.loads((root/n).read_text());digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
resolve=runpy.run_path(str(root/'scripts/resolve-evidence-history.py'))['resolve'];evidence={}
def add(name,sha=None):
 selected=resolve(str(name),sha) if sha else str(name);evidence[selected]=digest(selected)
 if sha:assert evidence[selected]==sha,name
def walk(value):
 if isinstance(value,list):
  for item in value:walk(item)
 elif isinstance(value,dict):
  for key,item in value.items():
   if isinstance(item,str) and isinstance(value.get(key+'_sha256'),str) and (root/item).is_file():add(item,value[key+'_sha256'])
   if key=='sha256':
    for field in ['source','path','file']:
     if field+'_sha256' not in value and isinstance(value.get(field),str) and (root/value[field]).is_file():add(value[field],item)
   if isinstance(item,str) and re.fullmatch('[a-f0-9]{64}',item) and (root/key).is_file():add(key,item)
   if isinstance(item,(dict,list)):walk(item)
def report(name):
 d=read(name);add(name);walk(d);return d
with (root/'runtime/session.lock').open('a') as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
report('artifacts/s2c-lifecycle-progress.json')
build=report('artifacts/xpc-activation-source-build.json');assert build['complete_source_files']==39 and build['original_exports_preserved']==630 and build['launch_reexports_preserved']==112
xpc=report('artifacts/xpc-activation-stage.json');kernel=report('artifacts/materialize-policy-kernel-build.json');assert kernel['complete_source_files']==879
materialize=report('artifacts/materialize-policy-stage.json')
before=report('artifacts/xpc-missing-service-baseline.json');after=report('artifacts/xpc-missing-service-fixed.json')
assert not before['verified'] and after['verified']
assert 'events=0 async=0 sync=0 timeouts=2' in (root/before['log']).read_text()
assert 'events=2 async=1 sync=1 timeouts=0' in (root/after['log']).read_text()
regressions=report('artifacts/xpc-activation-regressions.json');assert regressions['verified'] and len(regressions['results'])==3
policy=report('artifacts/materialize-policy-native-test.json');assert policy['verified'] and policy['checks']==1066
old_names=list((root/'artifacts').glob('xcode-service-runtime-xpc-activation-diagnostic-build-*.json'));assert len(old_names)==1
old_project=report(str(old_names[0].relative_to(root)));assert old_project['UTI_preflight_verified'] and not old_project['legacy_volume_API_prewarm_used']
old_text=(root/old_project['log']).read_text();assert 'materializationOffState == IOPOL_MATERIALIZE_DATALESS_FILES_OFF' in old_text
names=list((root/'artifacts').glob('xcode-service-runtime-materialize-policy-diagnostic-build-*.json'));assert len(names)==1
project_name=str(names[0].relative_to(root));project=report(project_name);assert project['UTI_preflight_verified'] and not project['legacy_volume_API_prewarm_used']
text=(root/project['log']).read_text()
assert 'materializationOffState ==' not in text and 'Stub called: initWithType: in MAAssetQuery' in text
assert 'downloadedAssets(assetType:attributesQuery:) leaked its continuation' in text
assert not re.search(r'^CompileC |^SwiftCompile ',text,re.M)
claim_name=next(n for n in project['service_logs'] if n.endswith('-filecoordination.log'));claim_text=(root/claim_name).read_text()
assert 'Handshake aborted as the connection has been invalidated' in claim_text
granted=re.findall(r'Claim ([A-F0-9-]+) granted in server',claim_text);invoked=re.findall(r'Claim ([A-F0-9-]+) invoked in server',claim_text)
assert len(granted)>=2 and set(granted)==set(invoked)
xcode={}
for mode in ['version','showsdks']:
 paths=list((root/'artifacts').glob('xcode-service-runtime-materialize-policy-'+mode+'-*.json'));assert len(paths)==1
 n=str(paths[0].relative_to(root));d=report(n);assert d['exit_status']==0 and d['UTI_preflight_verified'] and d['xcode_process_returned']
 xcode[mode]=dict(report=n,sha256=digest(n),exit_status=0)
for repo,name,files in [('libxpc','artifacts/libxpc-activation-failure-source.patch',[]),('xnu','artifacts/xnu-materialize-policy-source.patch',['darling/src/libsystem_kernel/emulation/include/common/tsd.h','darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/impl/misc/iopolicysys.c','libsyscall/wrappers/getiopolicy_np.c'])]:
 directory=root/'vendor/darling/src/external'/repo
 patch=subprocess.check_output(['git','-C',str(directory),'diff','HEAD',*(['--',*files] if files else [])],text=True)
 if not files:
  for path in subprocess.check_output(['git','-C',str(directory),'ls-files','--others','--exclude-standard'],text=True).splitlines():
   patch+=''.join(difflib.unified_diff([],(directory/path).read_text().splitlines(True),fromfile='/dev/null',tofile='b/'+path))
 (root/name).write_text(patch);add(name);subprocess.run(['git','-C',str(directory),'apply','--reverse','--check',str(root/name)],check=True)
for name in ['scripts/build-libxpc-source.py','scripts/build-libsystem-kernel-source.py','scripts/stage-xpc-activation-runtime.py','scripts/xpc-activation-runtime-profile.py','scripts/stage-materialize-runtime.py','scripts/materialize-runtime-profile.py','scripts/test-xpc-missing-service.py','scripts/test-xpc-activation-regressions.py','scripts/test-materialize-policy.py','scripts/probe-xcode-service-runtime.py','scripts/unrestricted-sandbox-runtime-profile.py','scripts/record-xpc-materialize-progress.py','scripts/resolve-evidence-history.py','fixtures/hello/xpc-missing-service.c','fixtures/hello/materialize-policy.c','vendor/darling/src/private-frameworks/MobileAsset/src/MAAssetQuery.m','vendor/darling/src/private-frameworks/MobileAsset/include/MobileAsset/MAAssetQuery.h','logs/foundation-materialize-function.log']:
 add(name)
 if name.endswith('.py'):ast.parse((root/name).read_text())
reference='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk/usr/include/'
for name in ['xpc/connection.h','sys/resource.h']:add(reference+name)
add('vendor/darling/src/external/xnu/bsd/kern/kern_resource.c')
p=runpy.run_path(str(root/'scripts/materialize-runtime-profile.py'))['profile']()
d=dict(checked_at=datetime.now(timezone.utc).isoformat(),goal_status='active',complete=False,full_xcode_build_ready=False,signing_ready=False,default_entry_promoted=False,
 previous_goal_turn_classification='progress',current_goal_turn_classification='progress',source_runtime=p['source_runtime'],source_xpc_activation=xpc,source_materialize_policy=materialize,
 source_libxpc_files=39,source_kernel_files=879,source_libxpc_exports_preserved=630,source_libxpc_launch_reexports_preserved=112,
 real_unknown_service_invalid_event_and_sync_async_errors_verified=True,explicit_cancel_errors_use_invalid_rather_than_interrupted=True,
 native_XPC_loopback_checkins=16,native_XPC_reply_payloads=256,native_connection_cancel_lifecycles=33,native_connection_concurrent_readers=8,native_shmem_lifecycles=32,native_malformed_shmem_packets=96,
 native_thread_materialization_checks=1066,native_thread_materialization_updates=512,native_thread_materialization_workers=8,
 materialization_process_scope_supported=False,dataless_file_provider_implemented=False,materialization_ORIG_modifier_supported=False,
 original_filecoordinationd_granted_actual_Xcode_claims=len(granted),original_filecoordinationd_invoked_actual_Xcode_claims=len(invoked),
 original_RunningBoard_service_available=False,original_RunningBoard_handshake_failure_handled=True,original_filecoordination_read_write_exclusion_fully_verified=False,
 original_Xcode_materialization_assertion_resolved=True,original_xcode_regressions=xcode,
 latest_original_project=dict(report=project_name,sha256=digest(project_name),exit_status=project['exit_status'],UTI_preflight_verified=True,xcode_process_returned=project['xcode_process_returned']),
 current_observed_failure='Original Xcode passes real file-access arbitration and the thread materialization assertion. It now calls the Darling MAAssetQuery initWithType: stub; downloadedAssets(assetType:attributesQuery:) leaks its Swift continuation. No compiler steps have executed.',
 diagnostic_build_uses_explicit_permissive_coreservices_policy=True,strict_Sandbox_enforcement_verified=False,actual_project_compilation_started=False,evidence=evidence,next_work=[
 'Implement actual MobileAsset query construction, local catalog/results and correctly typed async completion/error delivery for the original downloadedAssets caller; do not fabricate asset availability or download success.',
 'Retry the unchanged original project through actual compile/link, then Unity/CocoaPods, archive, signing and export. Add real coordinated read/write/exclusion coverage as FileCoordination is exercised.',
 'Complete process-scoped/ORIG materialization policies and actual dataless-provider behavior if needed, real RunningBoard monitoring, startup media/volumes, restrictive Sandbox and other earlier gaps; current valid thread policy values are DEFAULT/OFF/ON only.'
 ])
(root/'artifacts/xpc-activation-materialize-progress.json').write_text(json.dumps(d,indent=2)+'\n');print('Recorded',len(evidence),'hashes; native file-access claims granted/invoked; MobileAsset async query remains')
