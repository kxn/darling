#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
mkdir -p runtime/launchd-source/service-jobs
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -fblocks \
    -c fixtures/hello/xpc-service-source.c -o artifacts/xpc-service-source.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -L runtime/libxpc-source -lxpc -lSystem artifacts/xpc-service-source.o -o artifacts/xpc-service-source
export LINUXCODE_DARLING_SERVER="$project/runtime/darlingserver-source-build/darlingserver/darlingserver"
export LINUXCODE_LIBXPC="$project/runtime/libxpc-source/libxpc.dylib"
export LINUXCODE_LAUNCHD="$project/runtime/launchd-source/launchd"
timeout -k 5 90 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/xpc-service-source \
    /Volumes/SystemRoot/workspace/runtime/launchd-source/service-jobs > logs/xpc-service-source.log 2>&1
for marker in \
    XPC_SERVICE_API_OWNED_BY_ACTUAL_LIBXPC_BACKEND_OK \
    XPC_SERVICE_REAL_OBJECT_QUEUE_OWNERSHIP_UUID_AND_SPECIFIER_LIFECYCLE_OK \
    XPC_SERVICE_NATIVE_ENVELOPE_AND_REAL_AUDIT_REJECT_FORGED_PID1_REPLY_OK \
    XPC_SERVICE_REAL_LAUNCHD_MALFORMED_TYPED_REQUESTS_AND_UNSUPPORTED_ROUTINE_ERRORS_OK \
    XPC_SERVICE_REAL_LAUNCHD_START_REPEAT_AND_EIGHT_WAIT4_RESTARTS_OK \
    XPC_SERVICE_REAL_RESTART_SUSPENDS_BEFORE_USER_ENTRY_AND_TASK_RESUME_WORKS_OK \
    XPC_SERVICE_REAL_COLD_START_SUSPENSION_OK \
    XPC_SERVICE_REAL_MISSING_JOB_UNSUPPORTED_DOMAINS_AND_UNPRIVILEGED_DENIAL_OK; do
    rg -q "^${marker}$" logs/xpc-service-source.log
done
env -u LINUXCODE_LAUNCHD -u LINUXCODE_LIBSYSTEM_KERNEL -u LINUXCODE_QUARANTINE -u LINUXCODE_SANDBOX \
    timeout -k 5 20 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/xpc-service-source --timeout \
    > logs/xpc-service-source-legacy-timeout.log 2>&1
rg -q '^XPC_SERVICE_INCOMPATIBLE_LAUNCHD_REAL_TIMEOUT_OK$' logs/xpc-service-source-legacy-timeout.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess
r=Path.cwd(); digest=lambda p:hashlib.sha256((r/p).read_bytes()).hexdigest()
xpc=json.loads((r/'artifacts/libxpc-source.json').read_text())
launchd=json.loads((r/'artifacts/launchd-source.json').read_text())
assert digest('runtime/libxpc-source/libxpc.dylib')==xpc['library_sha256']
assert digest('runtime/launchd-source/launchd')==launchd['binary_sha256']
assert digest('runtime/launchd-source/darling-root/usr/lib/system/libxpc.dylib')==xpc['library_sha256']
for relative,value in xpc['source_files'].items():
    assert digest('vendor/darling/src/external/libxpc/'+relative)==value
for relative,value in xpc['modified_files'].items():
    assert digest('vendor/darling/src/external/libxpc/'+relative)==value
for relative,value in launchd['source_files'].items():assert digest(relative)==value
for relative,value in launchd['modified_files'].items():assert digest('vendor/darling/'+relative)==value
selected={}
for variable in ['LINUXCODE_DARLING_SERVER','LINUXCODE_LIBXPC','LINUXCODE_LAUNCHD',
        'LINUXCODE_LIBSYSTEM_KERNEL','LINUXCODE_QUARANTINE','LINUXCODE_SANDBOX']:
    if os.environ.get(variable):
        path=Path(os.environ[variable]);selected[variable]=dict(path=str(path.relative_to(r)),sha256=digest(path))
native_reports=['artifacts/xpc-service-native-analysis.json','artifacts/xpc-service-native-callers.json']
for relative in native_reports:
    item=json.loads((r/relative).read_text());assert digest(item['log'])==item['log_sha256']
logs=['logs/xpc-service-source.log','logs/xpc-service-source-legacy-timeout.log']
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),installed=False,full_service_management=False,
    source_libxpc_sha256=xpc['library_sha256'],source_launchd_sha256=launchd['binary_sha256'],
    source_server_sha256=digest('runtime/darlingserver-source-build/darlingserver/darlingserver'),
    fixture_sha256=digest('fixtures/hello/xpc-service-source.c'),binary_sha256=digest('artifacts/xpc-service-source'),
    native_abi_report='artifacts/xpc-service-native-analysis.json',
    native_callers_report='artifacts/xpc-service-native-callers.json',
    selected_runtime=selected,api_owner_matches_actual_xpc_release_backend=True,
    native_reports={p:digest(p) for p in native_reports},
    source_build_reports={p:digest(p) for p in ['artifacts/libxpc-source.json','artifacts/launchd-source.json']},
    test_driver_sha256=digest('scripts/test-xpc-service-source.sh'),
    real_launchd_job_start_repeat_and_eight_restarts_verified=True,
    actual_old_process_exit_before_replacement_verified=True,
    cold_and_restarted_actual_task_suspend_count_and_task_resume_verified=True,
    real_kernel_audit_rejects_forged_pid1_reply_verified=True,unprivileged_audit_denial_verified=True,
    native_envelope_verified=True,object_queue_uuid_specifier_lifetime_verified=True,
    real_typed_control_errors_and_unknown_routine_verified=True,
    incompatible_launchd_real_timeout_verified=True,
    logs={p:digest(p) for p in logs},full_xcode_build_ready=False,signing_ready=False,
    known_limits=['Managed system-domain jobs and existing PID XPC domains only; PID-domain positive execution not yet exercised.',
        'User/login/gui/rendezvous-token domains explicitly return ENOTSUP; no fallback to system namespace.',
        'Native attach/notification/configurable service-instance API is still unimplemented.',
        'Suspension uses the existing Mach task_suspend backend and debugger task_resume; SIGCONT did not resume this state in an earlier test.',
        'Only root Mach audit credentials authorized; entitlement-based authorization unsupported.',
        'A pending restart has one reply; simultaneous restart returns EBUSY. Request timeout does not undo a requested restart.',
        'Start acknowledgment reports a real forked PID, not successful execution or service check-in.'])
(r/'artifacts/xpc-service-source.json').write_text(json.dumps(report,indent=2)+'\n')
PY
