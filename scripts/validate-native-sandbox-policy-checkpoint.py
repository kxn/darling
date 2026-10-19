#!/usr/bin/env python3
"""Validate the current evidence and immutable inputs of earlier checkpoints."""
from pathlib import Path
import ast, fcntl, hashlib, json, subprocess, runpy
from datetime import datetime, timezone

root = Path(__file__).resolve().parent.parent
read = lambda n: json.loads((root / n).read_text())
digest = lambda n: hashlib.sha256((root / n).read_bytes()).hexdigest()
primary_name = 'artifacts/native-crypto-progress.json'
phase_name = 'artifacts/native-sandbox-policy-progress.json'
primary = read(primary_name); phase = read(phase_name)
launchd = read('artifacts/launchd-sandbox-progress.json')
fs = read('artifacts/sandbox-fs-progress.json')
current = read('artifacts/unrestricted-sandbox-fsevents-progress.json')
disk = read('artifacts/diskarbitration-log-compose-progress.json')
power = read('artifacts/iokitd-power-progress.json')
matching = read('artifacts/iokitd-matching-progress.json')
mounts = read('artifacts/mount-flags-progress.json')
s2c = read('artifacts/s2c-lifecycle-progress.json')
xpc_materialize = read('artifacts/xpc-activation-materialize-progress.json')
mobileasset_query=read('artifacts/mobileasset-query-progress.json')
icu_signal=read('artifacts/icu-signal-progress.json')
assert primary['icu_signal_progress']==icu_signal
assert icu_signal['native_ICU_checks']==157 and icu_signal['fatal_children_tested']==8
assert icu_signal['parent_and_sibling_fatal_signals_after_fix']==0
assert icu_signal['original_build_tasks_executed'] and icu_signal['original_SwiftBuild_service_started']
assert not icu_signal['actual_project_compilation_started']
assert primary['mobileasset_query_progress']==mobileasset_query
assert mobileasset_query['native_query_checks']==1823 and mobileasset_query['original_Xcode_MobileAsset_Swift_continuation_leak_resolved']
assert mobileasset_query['actual_query_test_peer_requests']==48
assert mobileasset_query['source_query_async_uses_sync_wire_on_dispatch_worker']
assert not mobileasset_query['actual_project_compilation_started'] and not mobileasset_query['asset_download_implemented']
assert primary['xpc_activation_materialize_progress']==xpc_materialize
fsevents_history=read('artifacts/fsevents-history-progress.json')
assert primary['fsevents_history_progress']==fsevents_history
assert primary['current_candidate_runtime']==fsevents_history['source_runtime']
assert fsevents_history['main_queue_CFRunLoop_history_consumer_terminates']
assert fsevents_history['corpse_map_native_checks']==1808
assert not fsevents_history['global_event_ids_implemented']
assert not fsevents_history['original_project_build_succeeded']
assert xpc_materialize['real_unknown_service_invalid_event_and_sync_async_errors_verified']
assert xpc_materialize['native_thread_materialization_checks']==1066
assert xpc_materialize['original_filecoordinationd_granted_actual_Xcode_claims']>=2
assert xpc_materialize['original_Xcode_materialization_assertion_resolved'] and not xpc_materialize['actual_project_compilation_started']
assert primary['s2c_lifecycle_progress']==s2c
assert s2c['stale_weak_thread_object_was_selected_for_remote_map']
assert s2c['original_filecoordinationd_received_actual_Xcode_claim'] and not s2c['original_filecoordinationd_granted_claim']
assert not s2c['public_API_calls_used_in_Xcode_launch'] and not s2c['actual_project_compilation_started']
assert primary['mount_flags_progress']==mounts
assert mounts['original_root_and_SystemRoot_descriptions_after_real_mount_verified']
assert mounts['actual_tmpfs_mount_remount_unmount_verified'] and not mounts['fabricated_mount_events']
assert not mounts['initial_existing_volume_discovery_verified'] and not mounts['actual_project_compilation_started']
assert primary['iokitd_matching_progress']==matching
assert matching['original_DiskArbitration_session_created'] and matching['native_matching_callbacks']==11
assert matching['all_128_notifier_receive_ports_destroyed'] and not matching['actual_Linux_media_discovery_implemented']
assert primary['iokitd_power_progress']==power
assert power['native_IORegisterForSystemPower_verified'] and power['native_connection_subscription_cycles']==128
assert power['daemon_receive_ports_before_cycles']==power['daemon_receive_ports_after_cycles']==12
assert not power['native_resume_notification_delivery_verified'] and not power['pre_suspend_permission_barrier_implemented']
assert primary['diskarbitration_log_compose_progress']==disk
assert disk['native_SystemConfiguration_store_checks']==16 and disk['send_compose_checks']==2295
assert disk['original_configd_logging_abort_resolved'] and not disk['IOPMrootDomain_present']
assert primary['unrestricted_sandbox_fsevents_progress'] == current
assert current['unrestricted_profile_attachment_verified'] and not current['restrictive_profile_attachment_verified']
assert current['diagnostic_fsevents_startup_abort_resolved'] and current['diagnostic_mount_count']==0
assert current['native_device_ABI_checks']==113 and current['real_linux_device_checks']==337
assert primary['goal_status'] == 'active' and not primary['complete']
assert primary['native_sandbox_policy_progress'] == phase
assert primary['launchd_sandbox_progress'] == launchd
assert primary['sandbox_fs_progress'] == fs and not fs['profile_application_implemented']
assert not phase['profile_application_implemented'] and not phase['operation_enforcement_implemented']
assert phase['real_coreservices_profile_decoded'] and phase['selected_launchd_compiles_out_sandbox_checks']
history = read('artifacts/native-crypto-before-policy-vm-history/manifest.json')
launchd_history = read('artifacts/sandbox-policy-before-launchd-history/manifest.json')
fs_history = read('artifacts/sandbox-before-fs-mutations-history/manifest.json')
old_primary = read(history[primary_name]['archived'])
previous_policy_primary = read(launchd_history[primary_name]['archived'])
previous_launchd_primary = read(fs_history[primary_name]['archived'])
old_directory = read('artifacts/fileidtree-directory-progress.json')
resolve=runpy.run_path(str(root/'scripts/resolve-evidence-history.py'))['resolve']
def verify_old(name,sha):
    selected=resolve(name,sha)
    assert digest(selected)==sha,name
for report in [primary]:
    for name,sha in report['evidence'].items():assert digest(name)==sha,name
for report in [icu_signal,old_primary,old_directory,previous_policy_primary,previous_launchd_primary,phase,launchd,fs,current,disk,power,matching,mounts,s2c,xpc_materialize,mobileasset_query]:
    for name,sha in report['evidence'].items():verify_old(name,sha)
scripts = {name for name in primary['evidence'] if name.endswith('.py')}
scripts.add('scripts/validate-native-sandbox-policy-checkpoint.py')
for name in scripts: ast.parse((root / name).read_text())
guarded = read('artifacts/native-crypto-recorder-guards.json')
protected = [primary_name, phase_name, 'artifacts/current-work-state.json',
             'artifacts/fileidtree-directory-progress.json','artifacts/unrestricted-sandbox-fsevents-progress.json','artifacts/sandbox-fs-progress.json','artifacts/diskarbitration-log-compose-progress.json','artifacts/iokitd-power-progress.json','artifacts/iokitd-matching-progress.json']
before = {name: digest(name) for name in protected}
protected.append('artifacts/mount-flags-progress.json')
protected.append('artifacts/s2c-lifecycle-progress.json')
protected.append('artifacts/xpc-activation-materialize-progress.json')
protected.append('artifacts/mobileasset-query-progress.json')
protected.append('artifacts/icu-signal-progress.json')
before = {name: digest(name) for name in protected}
for name in guarded:
    result = subprocess.run(['python3', str(root / name)], capture_output=True, text=True)
    assert result.returncode == 0 and 'Preserving the newer native cryptography checkpoint' in result.stdout, (name, result.stdout, result.stderr)
result = subprocess.run(['python3', str(root / 'scripts/record-native-sandbox-policy-progress.py')], capture_output=True, text=True)
assert result.returncode == 0 and 'Preserving the newer launchd Sandbox checkpoint' in result.stdout
result = subprocess.run(['python3', str(root / 'scripts/record-launchd-sandbox-progress.py')], capture_output=True, text=True)
assert result.returncode == 0 and 'Preserving the newer file-mutation Sandbox checkpoint' in result.stdout
result=subprocess.run(['python3',str(root/'scripts/record-sandbox-fs-progress.py')],capture_output=True,text=True)
assert result.returncode==0 and 'Preserving the newer unrestricted Sandbox and FSEvents checkpoint' in result.stdout
result=subprocess.run(['python3',str(root/'scripts/record-unrestricted-sandbox-fsevents-progress.py')],capture_output=True,text=True)
assert result.returncode==0 and 'Preserving the newer DiskArbitration and source log composition checkpoint' in result.stdout
result=subprocess.run(['python3',str(root/'scripts/record-diskarbitration-progress.py')],capture_output=True,text=True)
assert result.returncode==0 and 'Preserving the newer source iokitd power checkpoint' in result.stdout
result=subprocess.run(['python3',str(root/'scripts/record-iokitd-power-progress.py')],capture_output=True,text=True)
assert result.returncode==0 and 'Preserving the newer iokitd matching and notifyd checkpoint' in result.stdout
result=subprocess.run(['python3',str(root/'scripts/record-iokitd-matching-progress.py')],capture_output=True,text=True)
assert result.returncode==0 and 'Preserving the newer source mount flags and notifications checkpoint' in result.stdout
result=subprocess.run(['python3',str(root/'scripts/record-mount-flags-progress.py')],capture_output=True,text=True)
assert result.returncode==0 and 'Preserving the newer source S2C lifecycle checkpoint' in result.stdout
result=subprocess.run(['python3',str(root/'scripts/record-s2c-lifecycle-progress.py')],capture_output=True,text=True)
assert result.returncode==0 and 'Preserving the newer XPC activation and thread materialization checkpoint' in result.stdout
result=subprocess.run(['python3',str(root/'scripts/record-xpc-materialize-progress.py')],capture_output=True,text=True)
assert result.returncode==0 and 'Preserving the newer source MobileAsset query checkpoint' in result.stdout
result=subprocess.run(['python3',str(root/'scripts/record-mobileasset-query-progress.py')],capture_output=True,text=True)
assert result.returncode==0 and 'Preserving the newer original ICU and fatal signal checkpoint' in result.stdout
assert before == {name: digest(name) for name in protected}
with (root / 'runtime/session.lock').open('a') as lock: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
live = []
for path in Path('/proc').iterdir():
    if not path.name.isdigit(): continue
    try:
        if (path / 'comm').read_text().strip() in ['darlingserver', 'mldr']:
            live.append(path.name)
    except OSError: pass
assert not live, live
for name in ['bin/darling', 'bin/xcodebuild', 'scripts/runtime-ns.sh']:
    assert digest(name) == old_primary['evidence'][name], name
assert digest('runtime/darlingserver-source-build/darlingserver/darlingserver') == 'ae78babd377dd542788f321752b11e9dea6413ee49d1009f00df825fdd9efd6b'
for name in ['runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild',
             'runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild']:
    assert digest(name) == 'd6ceec0a4fa47e3f7a20c712d960ffb954b2246a2c94a0bf0818b2e8344065c5'
report = dict(checked_at=datetime.now(timezone.utc).isoformat(), primary_report=primary_name,
              primary_report_sha256=digest(primary_name), policy_report_sha256=digest(phase_name),
              current_file_hashes_verified=len(primary['evidence']), policy_file_hashes_verified=len(phase['evidence']),
              prior_native_crypto_evidence_verified=len(old_primary['evidence']),
              prior_policy_checkpoint_evidence_verified=len(previous_policy_primary['evidence']),
              prior_launchd_checkpoint_evidence_verified=len(previous_launchd_primary['evidence']),
              prior_directory_evidence_verified=len(old_directory['evidence']),
              launchd_file_hashes_verified=len(launchd['evidence']),
              filesystem_file_hashes_verified=len(fs['evidence']),
              unrestricted_fsevents_file_hashes_verified=len(current['evidence']),
              iokitd_matching_file_hashes_verified=len(matching['evidence']),supplemental_iokitd_power_recorder_preserved=True,
              mount_flags_file_hashes_verified=len(mounts['evidence']),supplemental_iokitd_matching_recorder_preserved=True,
              s2c_lifecycle_file_hashes_verified=len(s2c['evidence']),supplemental_mount_flags_recorder_preserved=True,
              icu_signal_file_hashes_verified=len(icu_signal['evidence']),supplemental_mobileasset_query_recorder_preserved=True,
              mobileasset_query_file_hashes_verified=len(mobileasset_query['evidence']),supplemental_xpc_materialize_recorder_preserved=True,
              xpc_activation_materialize_file_hashes_verified=len(xpc_materialize['evidence']),supplemental_s2c_lifecycle_recorder_preserved=True,
              iokitd_power_file_hashes_verified=len(power['evidence']),supplemental_diskarbitration_recorder_preserved=True,
              diskarbitration_file_hashes_verified=len(disk['evidence']),supplemental_unrestricted_fsevents_recorder_preserved=True,
              supplemental_filesystem_recorder_preserved=True,
              scripts_syntax_verified=len(scripts), historical_recorders_verified=len(guarded),
              supplemental_policy_recorder_preserved=True,
              supplemental_launchd_recorder_preserved=True,
              state_unchanged_by_legacy_recorders=True, runtime_lock_free=True,
              no_live_Darling_processes=True, default_entry_unchanged=True,
              shared_baseline_server_unchanged=True, original_xcode_unchanged=True,
              goal_complete=False, verifier_sha256=digest('scripts/validate-native-sandbox-policy-checkpoint.py'))
(root / 'artifacts/native-sandbox-policy-checkpoint-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
