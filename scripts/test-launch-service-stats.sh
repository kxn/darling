#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
mkdir -p runtime/launchd-source/test-jobs
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -fblocks \
    -c fixtures/hello/launch-service-stats.c -o artifacts/launch-service-stats.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -L runtime/libxpc-source -lxpc -lSystem artifacts/launch-service-stats.o -o artifacts/launch-service-stats
LINUXCODE_DARLING_SERVER="$project/runtime/darlingserver-source-build/darlingserver/darlingserver" \
LINUXCODE_LIBXPC="$project/runtime/libxpc-source/libxpc.dylib" \
LINUXCODE_LAUNCHD="$project/runtime/launchd-source/launchd" \
    timeout -k 5 60 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/launch-service-stats \
    /Volumes/SystemRoot/workspace/runtime/launchd-source/test-jobs > logs/launch-service-stats.log 2>&1
rg -q '^LAUNCH_STATS_REAL_LAUNCHD_WAIT4_JOBS_VERSIONS_2_TO_6_SIGNAL_REASON_AND_MONITOR_LIFECYCLE_OK$' logs/launch-service-stats.log
rg -q '^LAUNCH_STATS_REAL_JOB_RING_OVERFLOW_NEWEST_RECORDS_DROP_COUNT_AND_RESET_OK$' logs/launch-service-stats.log
rg -q '^LAUNCH_STATS_REAL_CONTROL_ERRORS_AND_READONLY_BUFFER_REJECTION_OK$' logs/launch-service-stats.log
rg -q '^LAUNCH_STATS_REAL_MACH_AUDIT_REJECTS_NON_PID1_PEER_WITH_FORGED_DICTIONARY_CREDENTIALS_OK$' logs/launch-service-stats.log
env -u LINUXCODE_LAUNCHD -u LINUXCODE_LIBSYSTEM_KERNEL -u LINUXCODE_QUARANTINE -u LINUXCODE_SANDBOX \
LINUXCODE_DARLING_SERVER="$project/runtime/darlingserver-source-build/darlingserver/darlingserver" \
LINUXCODE_LIBXPC="$project/runtime/libxpc-source/libxpc.dylib" \
    timeout -k 5 20 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/launch-service-stats --timeout \
    > logs/launch-service-stats-legacy-timeout.log 2>&1
rg -q '^LAUNCH_STATS_INCOMPATIBLE_PACKAGED_LAUNCHD_RETURNS_REAL_RECEIVE_TIMEOUT_OK$' logs/launch-service-stats-legacy-timeout.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess
r=Path.cwd();digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
launchd_path=r/'artifacts/launchd-source.json';launchd=json.loads(launchd_path.read_text())
xpc=json.loads((r/'artifacts/libxpc-source.json').read_text())
assert digest(r/'runtime/launchd-source/launchd')==launchd['binary_sha256']
assert digest(r/'runtime/launchd-source/darling-root/sbin/launchd')==launchd['binary_sha256']
assert digest(r/'runtime/launchd-source/darling-root/usr/lib/system/libxpc.dylib')==xpc['library_sha256']==launchd['source_libxpc_sha256']
for relative,value in launchd['source_files'].items():assert digest(r/relative)==value
for relative,value in launchd['modified_files'].items():assert digest(r/'vendor/darling'/relative)==value
original=launchd['source_configuration']
assert digest(r/original['original_launchd'])==original['original_launchd_sha256']
launchd.update(bootstrap_execution_verified=True,selected_live_service_statistics_verified=True,
    verified_at=datetime.now(timezone.utc).isoformat())
launchd_path.write_text(json.dumps(launchd,indent=2)+'\n')
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),installed=False,full_compatibility=False,
    selected_live_service_statistics_verified=True,full_darling_rebuild=False,
    source_launchd_sha256=launchd['binary_sha256'],source_libxpc_sha256=xpc['library_sha256'],
    source_server_sha256=digest(r/'runtime/darlingserver-source-build/darlingserver/darlingserver'),
    test_source_sha256=digest(r/'fixtures/hello/launch-service-stats.c'),test_binary_sha256=digest(r/'artifacts/launch-service-stats'),
    versions_verified=[2,3,4,5,6],native_wire_record_size=59,
    kernel_audit_trailer_credentials_and_pid1_reply_verification_exercised=True,
    genuine_launchctl_loaded_jobs_and_wait4_records_verified=True,
    signal_namespace_and_code_from_actual_wait_status_verified=True,
    monitor_lifecycle_errors_and_readonly_shmem_rejection_verified=True,
    ring_overflow_newest_records_drop_count_and_reset_verified=True,
    actual_non_pid1_peer_forged_payload_identity_rejected=True,
    incompatible_packaged_launchd_actual_receive_timeout_verified=True,
    record_extension_fields_implemented=False,unprivileged_entitlement_support=False,
    full_xcode_build_ready=False,signing_ready=False,log='logs/launch-service-stats.log',
    legacy_timeout_log='logs/launch-service-stats-legacy-timeout.log',
    known_limits=['Later per-platform record fields after the 37-byte prefix remain zero/unimplemented; no complete native record semantics claim.',
        'Only managed jobs reaped by actual successful wait4 contribute; synthetic/implicit reap and anonymous exits are not fabricated.',
        'Native entitlement verification is unavailable; root audit credentials are required and PID 1 root replies are checked. Non-root entitlement-based monitoring is unsupported.',
        'Monitors are bounded to 32, with at most 2^20 records each; larger capacities fail explicitly.',
        'Control requests have a 5-second receive timeout so an incompatible launchd cannot hang the caller indefinitely.',
        'Source client and launchd must be selected together; packaged defaults are unchanged.',
        'Untracked preexisting MAP_SHARED imports, complete Xcode SDK listing/project build/archive/signing remain incomplete.'])
(r/'artifacts/launch-service-stats.json').write_text(json.dumps(report,indent=2)+'\n')
repo=r/'vendor/darling'
patch=subprocess.check_output(['git','-C',str(repo),'diff','--binary','--','src/launchd'])
for relative in subprocess.check_output(['git','-C',str(repo),'ls-files','--others','--exclude-standard','--','src/launchd'],text=True).splitlines():
    patch+=subprocess.run(['git','diff','--no-index','--binary','--','/dev/null',relative],cwd=repo,stdout=subprocess.PIPE,check=False).stdout
(r/'artifacts/darling-launchd-service-stats.patch').write_bytes(patch)
subprocess.run(['git','-C',str(repo),'apply','--reverse','--check',str(r/'artifacts/darling-launchd-service-stats.patch')],check=True)
PY
