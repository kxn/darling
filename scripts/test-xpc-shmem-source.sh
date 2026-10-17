#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -fblocks \
    -c fixtures/hello/xpc-shmem-source.m -o artifacts/xpc-shmem-source.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -L runtime/libxpc-source -lxpc -L "$guest/usr/lib" -lobjc -lSystem \
    artifacts/xpc-shmem-source.o -o artifacts/xpc-shmem-source
expected_uuid=$(python3 - <<'PY'
from pathlib import Path
import struct
data=Path('runtime/libxpc-source/libxpc.dylib').read_bytes()
assert data[:4]==b'\xcf\xfa\xed\xfe'
offset=32
for _ in range(struct.unpack_from('<I',data,16)[0]):
    command,size=struct.unpack_from('<II',data,offset)
    if command==0x1b:
        print(data[offset+8:offset+24].hex());break
    offset+=size
else:raise ValueError('No source library UUID')
PY
)
LINUXCODE_DARLING_SERVER="$project/runtime/darlingserver-source-build/darlingserver/darlingserver" \
LINUXCODE_LIBXPC="$project/runtime/libxpc-source/libxpc.dylib" \
    timeout -k 5 60 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/xpc-shmem-source "$expected_uuid" \
    > logs/xpc-shmem-source.log 2>&1
rg -q '^XPC_SHMEM_SOURCE_LOADED_LIBRARY_UUID_VERIFIED$' logs/xpc-shmem-source.log
rg -q '^XPC_SHMEM_SOURCE_32_CYCLES_COPY_RIGHTS_PAGE_ROUNDING_ALIAS_READONLY_AND_WRONG_TYPES_OK$' logs/xpc-shmem-source.log
rg -q '^XPC_SHMEM_SOURCE_96_KERNEL_DELIVERED_MALFORMED_LENGTHS_AND_TRUNCATION_NO_RIGHT_LEAK_OK$' logs/xpc-shmem-source.log
rg -q '^XPC_SHMEM_SOURCE_REAL_XPC_DICTIONARY_OOL_PORTS_ROUNDTRIP_BIDIRECTIONAL_READONLY_AND_LIFETIME_OK$' logs/xpc-shmem-source.log
rg -q '^XPC_SHMEM_SOURCE_BACKING_FDS_RETURN_TO_BASELINE_AFTER_RECONCILIATION_OK$' logs/xpc-shmem-source.log
set +e
env -u LINUXCODE_LIBXPC -u LINUXCODE_DARLING_SERVER -u LINUXCODE_LAUNCHD -u LINUXCODE_LIBSYSTEM_KERNEL -u LINUXCODE_QUARANTINE -u LINUXCODE_SANDBOX \
    timeout -k 5 45 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/xpc-shmem-source "$expected_uuid" \
    > logs/xpc-shmem-source-default-uuid-rejection.log 2>&1
rejection_status=$?
set -e
[[ $rejection_status == 3 ]]
rg -q '^XPC_SHMEM_SOURCE_LOADED_LIBRARY_UUID_MISMATCH$' logs/xpc-shmem-source-default-uuid-rejection.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess
r=Path.cwd();p=r/'artifacts/libxpc-source.json';report=json.loads(p.read_text())
digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
assert digest(r/'runtime/libxpc-source/libxpc.dylib')==report['library_sha256']
assert digest(r/'runtime/libxpc-source/darling-root/usr/lib/system/libxpc.dylib')==report['library_sha256']
repo=r/'vendor/darling/src/external/libxpc'
for relative,value in {**report['source_files'],**report['modified_files']}.items():
    assert digest(repo/relative)==value, 'Source changed after libxpc build: '+relative
for relative,value in report['source_configuration']['base_libraries'].items():
    assert digest(r/relative)==value, 'Baseline runtime changed: '+relative
report.update(checked_at=datetime.now(timezone.utc).isoformat(),
    bootstrap_execution_verified=True,loaded_library_uuid_verified=True,
    default_library_rejected_by_source_uuid_guard=True,
    selected_xpc_shmem_execution_verified=True,full_xcode_build_ready=False,
    launch_service_statistics_report='artifacts/launch-service-stats.json',
    source_server_sha256=digest(r/'runtime/darlingserver-source-build/darlingserver/darlingserver'),
    test_binary_sha256=digest(r/'artifacts/xpc-shmem-source'),
    test_source_sha256=digest(r/'fixtures/hello/xpc-shmem-source.m'),
    test_utils_sha256=digest(r/'fixtures/hello/memory-entry-test-utils.h'),
    tests=['32 create/copy/map/release cycles; page-rounded length; same backing with bidirectional writes',
        'Copy owns a separate Mach send-right reference; pointer equality and port-based hash',
        'Read-only local and IPC mappings reject mprotect write escalation',
        'Wrong types and selected invalid arguments do not produce a mapping',
        '96 kernel-delivered malformed length/truncated packets reject and preserve send-right reference baseline',
        'Real forked processes exchange dictionaries with OOL port descriptors, deserialize, map and reply with the shared object',
        'Mappings remain usable after both endpoints release XPC objects and drain autorelease pools',
        'Backing FD count returns to baseline after each phase and deferred VM reconciliation',
        'Actual loaded library UUID matches the source build; default library is rejected'],
    known_limits=['Preexisting untracked MAP_SHARED anonymous/file mappings are not yet imported; the selected VM-allocated-page path is verified.',
        'Private anonymous-page conversion copies then remaps and is not atomic with concurrent writes.',
        'Full VM inheritance, parent-derived entries, COW/fixed mapping and maximum-execute policy remain unsupported.',
        'Existing external rich-error connection helper is still pinned to the packaged libxpc UUID; its connection APIs must not be used with this source variant until adapted.',
        'Selected launchd statistics support is recorded separately; later record extension fields and full Xcode project build/archive/signing remain incomplete.'],
    log='logs/xpc-shmem-source.log',negative_guard_log='logs/xpc-shmem-source-default-uuid-rejection.log')
p.write_text(json.dumps(report,indent=2)+'\n')
patch=subprocess.check_output(['git','-C',str(repo),'diff','--binary'])
for relative in subprocess.check_output(['git','-C',str(repo),'ls-files','--others','--exclude-standard'],text=True).splitlines():
    patch+=subprocess.run(['git','diff','--no-index','--binary','--','/dev/null',relative],cwd=repo,stdout=subprocess.PIPE,check=False).stdout
(r/'artifacts/darling-libxpc-shmem.patch').write_bytes(patch)
subprocess.run(['git','-C',str(repo),'apply','--reverse','--check',str(r/'artifacts/darling-libxpc-shmem.patch')],check=True)
PY
