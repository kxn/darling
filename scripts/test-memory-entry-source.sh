#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" \
    -c fixtures/hello/memory-entry-source.c -o artifacts/memory-entry-source.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -lSystem artifacts/memory-entry-source.o -o artifacts/memory-entry-source
LINUXCODE_DARLING_SERVER="$project/runtime/darlingserver-source-build/darlingserver/darlingserver" \
    timeout -k 5 60 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/memory-entry-source \
    > logs/memory-entry-source.log 2>&1
rg -q '^MEMORY_ENTRY_SOURCE_ALIAS_SUBRANGE_PARTIAL_UNMAP_READONLY_NO_WRITE_ESCALATION_32_CYCLES_FD_CLEANUP_OK$' logs/memory-entry-source.log
rg -q '^MEMORY_ENTRY_SOURCE_REAL_INTERPROCESS_MACH_CAPABILITY_BIDIRECTIONAL_SHARING_AFTER_PORT_RELEASE_OK$' logs/memory-entry-source.log
rg -q '^MEMORY_ENTRY_SOURCE_ADDRESS_REUSE_INVALID_CAPABILITIES_FLAGS_BOUNDS_AND_32_CONCURRENT_MAPS_OK$' logs/memory-entry-source.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess
r=Path.cwd();c=json.loads(Path('config/darlingserver-source-build.json').read_text())
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(r/c['runtime_binary'])==c['runtime_binary_sha256']
files=subprocess.check_output(['git','-C',c['server_source'],'diff','--name-only'],text=True).splitlines()
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),installed=False,
    full_compatibility=False,full_darling_rebuild=False,full_server_source_build=True,
    source_commit=c['server_commit'],source_files={p:digest(r/c['server_source']/p) for p in files},
    source_binary=c['source_binary'],source_binary_sha256=digest(r/c['source_binary']),
    default_server_unchanged=True,default_server_sha256=digest(r/c['runtime_binary']),
    private_mount_only=True,selected_memory_entry_execution_verified=True,
    test_binary_sha256=digest(r/'artifacts/memory-entry-source'),
    test_source_sha256=digest(r/'fixtures/hello/memory-entry-source.c'),
    lifecycle_cycles=32,concurrent_maps=32,concurrent_threads=4,
    real_cross_process_capability_transfer_and_bidirectional_sharing_verified=True,
    readonly_mapping_cannot_become_writable_via_mprotect_verified=True,
    address_reuse_identity_and_offset_reconciliation_verified=True,
    backend_fd_count_returns_to_baseline_after_reconciliation_verified=True,
    vm_prot_is_mask_mapping_intersection_verified=True,
    xpc_shared_memory_class_source='artifacts/libxpc-source.json',launch_service_statistics_report='artifacts/launch-service-stats.json',
    full_xcode_build_ready=False,log='logs/memory-entry-source.log',
    known_limits=[
        'Default runtime still uses the packaged server. Source server is selected only with LINUXCODE_DARLING_SERVER and a private bind mount.',
        'Source server now reports x86_64h only after real CPUID feature and OS XMM/YMM checks. Execution regression is recorded separately in logs/source-runtime-host-cpu.log.',
        'Local optimized/raw unmaps are reconciled on subsequent memory-entry operations; they do not currently send immediate server notifications.',
        'Converting anonymous pages into memfd-backed sharing copies then replaces the mapping. Concurrent writes during this conversion are not atomic.',
        'Parent-entry derivation, COW/fixed/complex-alignment mappings and importing untracked preexisting shared-file mappings return explicit unsupported errors.',
        'Full VM inheritance and maximum-execute-protection policy are not implemented by this change.',
        'Selected XPC shared-memory object and IPC execution is recorded separately; preexisting untracked MAP_SHARED import and launchd control/statistics remain incomplete.'])
Path('artifacts/darlingserver-memory-entry.json').write_text(json.dumps(report,indent=2)+'\n')
PY
