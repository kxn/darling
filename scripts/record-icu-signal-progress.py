#!/usr/bin/env python3
"""Record the original build's real crash fixes and first executed build tasks."""
from pathlib import Path
from datetime import datetime,timezone
import ast,fcntl,hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
read=lambda n:json.loads((root/n).read_text());digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest();resolve=runpy.run_path(str(root/'scripts/resolve-evidence-history.py'))['resolve'];evidence={}
def add(n,sha=None):
 n=resolve(str(n),sha) if sha else str(n);evidence[n]=digest(n)
 if sha:assert evidence[n]==sha,n
def walk(d):
 if isinstance(d,list):
  for v in d:walk(v)
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
previous=report('artifacts/mobileasset-query-progress.json');kernel=report('artifacts/fatal-signal-kernel-build.json');assert kernel['complete_source_files']==879
for n in ['artifacts/icu-data-stage.json','artifacts/fatal-signal-stage.json','artifacts/system-version-stage.json','artifacts/swb-logging-stage.json','artifacts/swb-swift-logging-stage.json']:report(n)
for target,provider in [('oslog-build-service-native','/System/Library/Frameworks/OSLog.framework/Versions/A/OSLog'),('swift-oslog-build-service-native','/usr/lib/swift/libswiftOSLog.dylib')]:
 image=report('runtime/rebuilt-'+target+'/reconstruction.json');add('runtime/fullsystem-libraries'+provider,image['original_image_sha256']);assert not image['backend_call_overrides'] and not image['redirected_imports']
before=report('artifacts/icu-data-security-baseline.json');after=report('artifacts/icu-data-security-fixed.json')
assert before['exit_status']==2 and 'ICU_NATIVE_SYSTEM_NUMBER_FORMATTER_NULL' in (root/before['log']).read_text()
assert after['verified'] and after['checks']==[149,157]
fatal_before=report('artifacts/fatal-signal-isolation-baseline.json');fatal_after=report('artifacts/fatal-signal-isolation-fixed.json');assert fatal_before['exit_status']==2 and fatal_after['verified']
assert 'PARENT_SEGV=4 PARENT_ABRT=8 SIBLING_SEGV=4 SIBLING_ABRT=8' in (root/fatal_before['log']).read_text()
assert 'PARENT_SEGV=0 PARENT_ABRT=0 SIBLING_SEGV=0 SIBLING_ABRT=0' in (root/fatal_after['log']).read_text()
binding=report('artifacts/system-version-binding-test.json');assert binding['verified'];assert digest(binding['unmodified_prefix_metadata'])==binding['unmodified_prefix_metadata_sha256']
trace=report('artifacts/xcode-after-start-trace.json');fault=report('artifacts/xcode-input-fault-capture.json');assert trace['wrapper_exit_status']==1 and fault['capture_exit_status']==0
for pid in [505100,505101,505102,505794,506955,506956,507143,507144]:add('logs/xcode-after-start.strace.'+str(pid))
t=(root/'logs/xcode-after-start.strace.505794').read_text();assert 'si_addr=0x8' in t and 'kill(0, SIGSEGV)' in t
assert 'read(3, "", 4)' in (root/'logs/xcode-after-start.strace.505100').read_text()
symbols=report('artifacts/xcode-input-options-fault-symbolication.json');text=(root/symbols['output']).read_text()
for n in ['__CFGetNonObjCTypeID','_SecKeyParamsGetCFIndex','_SecKeyCreateWithData','SecurityRSAPublicKey']:assert n in text,n
projects=[]
for pattern in ['xcode-service-runtime-fatal-signal-diagnostic-build-*.json','xcode-service-runtime-system-version-diagnostic-build-*.json','xcode-service-runtime-swb-logging-diagnostic-build-*.json','xcode-service-runtime-swb-swift-logging-diagnostic-build-*.json']:
 for path in sorted((root/'artifacts').glob(pattern)):
  name=str(path.relative_to(root));d=report(name);assert d['UTI_preflight_verified'] and not d['legacy_volume_API_prewarm_used'] and d['xcode_process_returned']
  projects.append(dict(report=name,sha256=digest(name),exit_status=d['exit_status'],xcode_process_returned=True,UTI_preflight_verified=True))
latest=next(p for p in projects if 'swb-swift-logging-diagnostic-build' in p['report']);d=read(latest['report']);text=(root/d['log']).read_text()
for marker in ['ComputePackagePrebuildTargetDependencyGraph','CreateBuildRequest','CreateBuildOperation','ComputeTargetDependencyGraph','CreateBuildDescription','CreateBuildDirectory','WriteAuxiliaryFile','ClangStatCache','Symbol not found: _FSEventsGetCurrentEventId','SERVICE_RUNTIME_XCODE_STATUS 65']:assert marker in text,marker
assert 'Unable to parse product build version' not in text and 'Library not loaded: /usr/lib/swift/libswiftOSLog.dylib' not in text
assert not re.search(r'^CompileC |^SwiftCompile ',text,re.M)
outputs=[];destination=root/'artifacts/icu-signal-build-output-snapshot';destination.mkdir(exist_ok=True)
for path in sorted((root/'runtime/xcode-service-runtime/DerivedData/Build/Intermediates.noindex').rglob('*')):
 if not path.is_file() or path.suffix not in ['.hmap','.resp','.json']:continue
 if path.suffix=='.json' and path.name not in ['manifest.json','build-request.json']:continue
 data=path.read_bytes();sha=hashlib.sha256(data).hexdigest();snapshot=destination/sha;snapshot.write_bytes(data);add(str(snapshot.relative_to(root)))
 outputs.append(dict(source_path=str(path.relative_to(root)),path=str(snapshot.relative_to(root)),sha256=sha,size=len(data),source_mtime=path.stat().st_mtime))
assert len([p for p in outputs if p['source_path'].endswith('.hmap')])==6 and len(outputs)>=9
xcode={}
for mode in ['version','showsdks']:
 paths=list((root/'artifacts').glob('xcode-service-runtime-swb-swift-logging-'+mode+'-*.json'));assert len(paths)==1
 n=str(paths[0].relative_to(root));d=report(n);assert d['exit_status']==0 and d['xcode_process_returned'] and d['UTI_preflight_verified'];xcode[mode]=dict(report=n,sha256=digest(n),exit_status=0)
for n in ['scripts/capture-darling-process-tree.py','scripts/trace-xcode-after-start.py','scripts/capture-xcode-input-fault.py','scripts/stage-icu-data-runtime.py','scripts/icu-data-runtime-profile.py','scripts/test-icu-data-security.py','scripts/stage-fatal-signal-runtime.py','scripts/fatal-signal-runtime-profile.py','scripts/test-fatal-signal-isolation.py','scripts/stage-system-version-runtime.py','scripts/system-version-runtime-profile.py','scripts/test-system-version-binding.py','scripts/stage-swb-logging-runtime.py','scripts/swb-logging-runtime-profile.py','scripts/stage-swb-swift-logging-runtime.py','scripts/swb-swift-logging-runtime-profile.py','scripts/probe-xcode-service-runtime.py','scripts/runtime-system-version-ns.sh','bin/darling-system-version','scripts/record-icu-signal-progress.py','scripts/resolve-evidence-history.py','fixtures/hello/icu-data-security.m','fixtures/hello/fatal-signal-isolation.c','fixtures/hello/system-version-resource.m','artifacts/xcode-initialization-initial-history/manifest.json','config/cache-image-pins.json','logs/rebuild-oslog-build-service-native.log','logs/rebuild-swift-oslog-build-service-native.log']:
 add(n)
 if n.endswith('.py'):ast.parse((root/n).read_text())
subprocess.run(['bash','-n',str(root/'scripts/runtime-system-version-ns.sh')],check=True)
source='vendor/darling/src/external/xnu';files=['darling/src/libsystem_kernel/emulation/src/linux_premigration/signal/sigexc.c','darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/impl/misc/abort_with_payload.c'];patch='artifacts/xnu-fatal-signal-isolation-source.patch'
(root/patch).write_bytes(subprocess.check_output(['git','-C',str(root/source),'diff','HEAD','--',*files]));subprocess.run(['git','-C',str(root/source),'apply','--reverse','--check',str(root/patch)],check=True);add(patch)
p=runpy.run_path(str(root/'scripts/swb-swift-logging-runtime-profile.py'))['profile']()
d=dict(checked_at=datetime.now(timezone.utc).isoformat(),goal_status='active',complete=False,full_xcode_build_ready=False,signing_ready=False,default_entry_promoted=False,previous_goal_turn_classification='progress',current_goal_turn_classification='progress',
 source_runtime=p['source_runtime'],source_fatal_signal=p['source_fatal_signal'],original_icu_data=p['original_icu_data'],original_system_version=p['original_system_version'],original_swb_logging=p['original_swb_logging'],original_swb_swift_logging=p['original_swb_swift_logging'],
 experimental_runtime_wrapper='bin/darling-system-version',default_runtime_wrapper_unchanged=True,persistent_system_version_unchanged=True,private_system_version_is_original_reference_metadata=True,
 source_kernel_files=879,native_ICU_version='78.1.0.0',native_ICU_checks=157,native_number_roundtrips=36,native_number_locales=4,native_RSA_import_and_OpenSSL_signature_verification=True,native_RSA_modified_message_rejected=True,
 fatal_children_tested=8,default_fatal_signal_no_longer_targets_whole_process_group=True,abort_with_payload_no_longer_targets_whole_process_group=True,parent_and_sibling_fatal_signals_after_fix=0,
 early_dyld_variant_fatal_signal_paths_verified=False,default_stop_and_Darwin_tracer_group_signal_paths_fixed=False,abort_ignored_SIGABRT_semantics_implemented=False,
 original_Xcode_null_formatter_certificate_import_crash_resolved=True,old_wrapper_exit_1_was_not_proof_of_a_persistent_wait=True,
 original_OSLog_exports=67,original_OSLog_classes=11,original_swiftOSLog_exports=13,original_log_backend_calls_preserved=True,full_OSLog_or_logd_service_semantics_verified=False,
 original_SwiftBuild_service_started=True,original_build_description_created=True,original_build_tasks_executed=True,original_build_output_snapshots=outputs,original_xcode_regressions=xcode,original_project_attempts=projects,latest_original_project=latest,
 actual_project_compilation_started=False,actual_project_linking_completed=False,original_project_build_succeeded=False,
 current_observed_failure='The unchanged original SWBBuildService computes the dependency graph and build description, executes directory/header-map/response-file tasks and announces compiler/linker probes. Its ClangStatCache task fails because clang-stat-cache cannot resolve FSEventsGetCurrentEventId through the selected CoreServices umbrella. No CompileC/SwiftCompile or successful link was observed.',
 diagnostic_build_uses_explicit_permissive_coreservices_policy=True,strict_Sandbox_enforcement_verified=False,evidence=evidence,next_work=[
 'Restore the genuine FSEventsGetCurrentEventId API and CoreServices umbrella export path required by original clang-stat-cache. Audit its other FSEvents imports and cache invalidation/replay semantics against actual Linux events; do not disable the cache, return a fabricated event ID or change the original build arguments.',
 'Retry unchanged XcodeSmoke through actual CompileC/link and verify the produced program. Preserve real build-service task execution and inspect child environment selection as needed. CoreSimulator service bootstrap and CreatedByBuildSystem xattr warnings remain unresolved.',
 'Continue full Unity/CocoaPods, iOS/macOS archive, signing and export; complete restrictive Sandbox, startup volumes, actual RunningBoard monitoring and other recorded runtime gaps. Current original RSA verification is not a signing/keychain/provisioning completion claim.'
 ])
(root/'artifacts/icu-signal-progress.json').write_text(json.dumps(d,indent=2)+'\n');print('Recorded',len(evidence),'hashes;',len(outputs),'real build outputs; clang-stat-cache FSEvents export remains')
