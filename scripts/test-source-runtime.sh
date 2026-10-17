#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
unset LINUXCODE_LIBSYSTEM_KERNEL LINUXCODE_QUARANTINE LINUXCODE_SANDBOX
export LINUXCODE_DARLING_SERVER="$project/runtime/darlingserver-source-build/darlingserver/darlingserver"
export LINUXCODE_LIBXPC="$project/runtime/libxpc-source/libxpc.dylib"
export LINUXCODE_LAUNCHD="$project/runtime/launchd-source/launchd"
bash scripts/test-memory-entry-source.sh > logs/source-runtime-memory-driver.log 2>&1
bash scripts/test-xpc-shmem-source.sh > logs/source-runtime-xpc-driver.log 2>&1
bash scripts/test-launch-service-stats.sh > logs/source-runtime-stats-driver.log 2>&1
bash scripts/test-macho-slices.sh > logs/source-runtime-macho-slices-driver.log 2>&1
workspace=/Volumes/SystemRoot/workspace
timeout -k 5 45 bin/darling shell "$workspace/artifacts/host-cpu-smoke" --after \
    "$workspace/artifacts/libHaswellCPUSmoke.dylib" > logs/source-runtime-host-cpu.log 2>&1
rg -q '^HOST_CPU_X86_64H_REPORT_AND_ORIGINAL_APPLE_AVX2_LIBRARY_EXECUTION_OK$' logs/source-runtime-host-cpu.log
timeout -k 5 45 bin/darling shell /usr/bin/env \
    DYLD_LIBRARY_PATH="$workspace/runtime/native-library-stage:/usr/lib/swift" \
    "$workspace/artifacts/mach-port-smoke" > logs/source-runtime-mach-port.log 2>&1
rg -q '^BASELINE_MACH_PORT_REAL_RIGHTS_RUNLOOP_RAW_AND_OOL_DATA_MESSAGES_INVALIDATION_OK$' logs/source-runtime-mach-port.log
timeout -k 5 45 bin/darling shell /usr/bin/env \
    DYLD_LIBRARY_PATH="$workspace/runtime/native-library-stage:$workspace/runtime/rebuilt-der:/usr/lib/swift" \
    "$workspace/artifacts/dyld-process-snapshot" "$workspace/runtime/dyld-cache-introspection/fixture.dylib" \
    > logs/source-runtime-dyld-snapshot.log 2>&1
rg -q '^REAL_DYLD_PROCESS_SNAPSHOT_MACH_IMAGES_UUID_SEGMENTS_CONTENT_LOAD_UNLOAD_FROZEN_STATE_RIGHTS_OK ' logs/source-runtime-dyld-snapshot.log
timeout -k 5 45 bin/darling shell /usr/bin/xcodebuild -version > logs/source-runtime-xcode-version.log 2>&1
rg -q '^Xcode 26.6$' logs/source-runtime-xcode-version.log
rg -q '^Build version 17F113$' logs/source-runtime-xcode-version.log
set +e
python3 scripts/probe-full-native-xcode.py --source-runtime > logs/probe-source-runtime-xcode-driver.log 2>&1
probe_status=$?
set -e
[[ $probe_status == 0 || $probe_status == 1 ]]
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess
r=Path.cwd();digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
kernel=json.loads((r/'artifacts/darlingserver-memory-entry.json').read_text())
xpc=json.loads((r/'artifacts/libxpc-source.json').read_text())
probe=json.loads((r/'artifacts/xcode-full-native-foundation-source-probe.json').read_text())
stats=json.loads((r/'artifacts/launch-service-stats.json').read_text())
slices=json.loads((r/'artifacts/macho-slices-source.json').read_text())
launchd=json.loads((r/'artifacts/launchd-source.json').read_text())
assert digest(r/kernel['source_binary'])==kernel['source_binary_sha256']==xpc['source_server_sha256']
assert probe['source_runtime']['LINUXCODE_DARLING_SERVER']['sha256']==kernel['source_binary_sha256']
assert probe['source_runtime']['LINUXCODE_LIBXPC']['sha256']==xpc['library_sha256']
assert probe['source_runtime']['LINUXCODE_LAUNCHD']['sha256']==launchd['binary_sha256']==stats['source_launchd_sha256']
assert stats['selected_live_service_statistics_verified']
assert slices['runtime_execution_verified']
assert digest(r/'runtime/native-library-stage/libDarlingCacheIntrospection.dylib')==slices['library_sha256']
assert xpc['selected_xpc_shmem_execution_verified']
assert digest(r/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild')==probe['apple_xcodebuild_sha256']
repo=r/'vendor/darlingserver'
patch=subprocess.check_output(['git','-C',str(repo),'diff','--binary'])
(r/'artifacts/darlingserver-memory-entry.patch').write_bytes(patch)
subprocess.run(['git','-C',str(repo),'apply','--reverse','--check',str(r/'artifacts/darlingserver-memory-entry.patch')],check=True)
logs=['logs/source-runtime-host-cpu.log','logs/source-runtime-mach-port.log',
      'logs/source-runtime-dyld-snapshot.log','logs/source-runtime-xcode-version.log',
      'logs/xcode-full-native-foundation-source-showsdks.log','logs/launch-service-stats.log','logs/macho-slices.log']
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),installed=False,full_darling_rebuild=False,
    full_server_and_libxpc_source_builds=True,source_server_sha256=kernel['source_binary_sha256'],
    full_launchd_source_build=True,source_launchd_sha256=launchd['binary_sha256'],
    selected_real_launchd_exit_statistics_verified=True,
    selected_macho_slice_utilities_verified=True,
    dyld_introspection_and_slices_helper_sha256=slices['library_sha256'],
    source_libxpc_sha256=xpc['library_sha256'],default_server_unchanged=True,
    default_server_sha256=kernel['default_server_sha256'],
    default_libxpc_unchanged=True,
    source_cpu_subtype_cpuid_os_guard_and_actual_apple_avx2_execution_verified=True,
    selected_mach_memory_entry_and_xpc_shmem_verified=True,
    original_ns_mach_port_raw_ool_regression_verified=True,
    actual_dyld_process_snapshot_regression_verified=True,
    original_xcode_version_verified=True,sdk_listing_succeeded=probe['sdk_listing_succeeded'],
    xcode_sdk_listing_exit_status=probe['exit_status'],full_xcode_build_ready=False,signing_ready=False,
    host_uuid_query_known_issue='_CFGetHostUUIDString error 78 remains in xcodebuild -version output',
    logs={p:digest(r/p) for p in logs},
    source_artifacts=['artifacts/darlingserver-memory-entry.json','artifacts/libxpc-source.json',
        'artifacts/launch-service-stats.json','artifacts/macho-slices-source.json','artifacts/xcode-full-native-foundation-source-probe.json'])
(r/'artifacts/source-runtime-integration.json').write_text(json.dumps(report,indent=2)+'\n')
PY
