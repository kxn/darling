#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
unset LINUXCODE_QUARANTINE LINUXCODE_SANDBOX
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" \
    -c fixtures/hello/libsystem-kernel-source.c -o artifacts/libsystem-kernel-source.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -lSystem artifacts/libsystem-kernel-source.o -o artifacts/libsystem-kernel-source
source_uuid=$(python3 - <<'PY'
import re,subprocess
text=subprocess.check_output(['llvm-dwarfdump-19','--uuid','runtime/libsystem-kernel-source/libsystem_kernel.dylib'],text=True)
uuid=re.search(r'UUID: ([0-9A-F-]+) \(x86_64\)',text)[1]
print(uuid.replace('-','').lower())
PY
)
xpc_uuid=$(python3 - <<'PY'
import re,subprocess
text=subprocess.check_output(['llvm-dwarfdump-19','--uuid','runtime/libxpc-source/libxpc.dylib'],text=True)
print(re.search(r'UUID: ([0-9A-F-]+) \(x86_64\)',text)[1].replace('-','').lower())
PY
)
export LINUXCODE_DARLING_SERVER="$project/runtime/darlingserver-source-build/darlingserver/darlingserver"
export LINUXCODE_LIBXPC="$project/runtime/libxpc-source/libxpc.dylib"
export LINUXCODE_LAUNCHD="$project/runtime/launchd-source/launchd"
export LINUXCODE_LIBSYSTEM_KERNEL="$project/runtime/libsystem-kernel-source/libsystem_kernel.dylib"
workspace=/Volumes/SystemRoot/workspace
timeout -k 5 45 bin/darling shell "$workspace/artifacts/libsystem-kernel-source" "$source_uuid" \
    > logs/libsystem-kernel-source-spawn.log 2>&1
rg -q '^SOURCE_KERNEL_REAL_SPAWN_EXEC_PIPE_SIGNAL_MASK_PGROUP_WAIT_STATUS_ERRNO_SELECT_OK$' logs/libsystem-kernel-source-spawn.log
rg -q '^SOURCE_KERNEL_REAL_SHEBANG_WHITESPACE_INTERPRETER_ARGUMENT_AND_TEXT_FALLBACK_OK$' logs/libsystem-kernel-source-spawn.log
set +e
env -u LINUXCODE_LIBSYSTEM_KERNEL timeout -k 5 30 bin/darling shell \
    "$workspace/artifacts/libsystem-kernel-source" "$source_uuid" \
    > logs/libsystem-kernel-source-default-rejection.log 2>&1
rejection_status=$?
set -e
[[ $rejection_status == 88 ]]
rg -q '^SOURCE_KERNEL_UUID_REJECTED$' logs/libsystem-kernel-source-default-rejection.log
timeout -k 5 45 bin/darling shell /usr/bin/xcodebuild -version \
    > logs/libsystem-kernel-source-xcode-version.log 2>&1
rg -q '^Xcode 26.6$' logs/libsystem-kernel-source-xcode-version.log
rg -q '^Build version 17F113$' logs/libsystem-kernel-source-xcode-version.log
# Reuse actual existing integration binaries, without overwriting their reports
# about the different runtime that originally built and tested them.
timeout -k 5 60 bin/darling shell "$workspace/artifacts/memory-entry-source" \
    > logs/libsystem-kernel-source-memory-entry.log 2>&1
rg -q '^MEMORY_ENTRY_SOURCE_ALIAS_SUBRANGE_PARTIAL_UNMAP_READONLY_NO_WRITE_ESCALATION_32_CYCLES_FD_CLEANUP_OK$' logs/libsystem-kernel-source-memory-entry.log
timeout -k 5 60 bin/darling shell "$workspace/artifacts/xpc-shmem-source" "$xpc_uuid" \
    > logs/libsystem-kernel-source-xpc-shmem.log 2>&1
rg -q '^XPC_SHMEM_SOURCE_LOADED_LIBRARY_UUID_VERIFIED$' logs/libsystem-kernel-source-xpc-shmem.log
rg -q '^XPC_SHMEM_SOURCE_32_CYCLES_COPY_RIGHTS_PAGE_ROUNDING_ALIAS_READONLY_AND_WRONG_TYPES_OK$' logs/libsystem-kernel-source-xpc-shmem.log
rg -q '^XPC_SHMEM_SOURCE_96_KERNEL_DELIVERED_MALFORMED_LENGTHS_AND_TRUNCATION_NO_RIGHT_LEAK_OK$' logs/libsystem-kernel-source-xpc-shmem.log
rg -q '^XPC_SHMEM_SOURCE_REAL_XPC_DICTIONARY_OOL_PORTS_ROUNDTRIP_BIDIRECTIONAL_READONLY_AND_LIFETIME_OK$' logs/libsystem-kernel-source-xpc-shmem.log
rg -q '^XPC_SHMEM_SOURCE_BACKING_FDS_RETURN_TO_BASELINE_AFTER_RECONCILIATION_OK$' logs/libsystem-kernel-source-xpc-shmem.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess
r=Path.cwd();p=r/'artifacts/libsystem-kernel-source.json';report=json.loads(p.read_text())
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(r/'runtime/libsystem-kernel-source/libsystem_kernel.dylib')==report['binary_sha256']
assert digest(r/'runtime/libsystem-kernel-source/darling-root/usr/lib/system/libsystem_kernel.dylib')==report['binary_sha256']
assert digest(r/report['source_configuration']['baseline'])==report['source_configuration']['baseline_sha256']
for source in report['sources']:assert digest(r/source['source'])==source['sha256']
logs=['logs/libsystem-kernel-source-spawn.log','logs/libsystem-kernel-source-default-rejection.log',
      'logs/libsystem-kernel-source-xcode-version.log','logs/libsystem-kernel-source-memory-entry.log',
      'logs/libsystem-kernel-source-xpc-shmem.log']
report.update(runtime_execution_verified=True,verified_at=datetime.now(timezone.utc).isoformat(),
    loaded_source_uuid_and_packaged_library_rejection_verified=True,
    real_spawn_exec_pipe_signal_mask_process_group_wait_errno_and_select_verified=True,
    actual_shebang_whitespace_interpreter_argument_and_text_fallback_verified=True,
    original_xcodebuild_version_verified=True,logs={p:digest(r/p) for p in logs},
    xcode_sdk_listing_ready=False,full_xcode_build_ready=False,signing_ready=False,
    selected_runtime={key:dict(path=value,sha256=digest(r/value)) for key,value in {
        'darlingserver':'runtime/darlingserver-source-build/darlingserver/darlingserver',
        'libxpc':'runtime/libxpc-source/libxpc.dylib','launchd':'runtime/launchd-source/launchd'}.items()},
    test_source_sha256=digest(r/'fixtures/hello/libsystem-kernel-source.c'),
    test_binary_sha256=digest(r/'artifacts/libsystem-kernel-source'),
    remaining_work=['Selected responsibility APIs are verified separately in artifacts/responsibility-source.json; this suite uses packaged Quarantine.',
                    'Full original xcodebuild SDK listing, project build, archive and signing remain incomplete.'])
p.write_text(json.dumps(report,indent=2)+'\n')
repo=r/'vendor/darling/src/external/xnu'
patch=subprocess.check_output(['git','-C',str(repo),'diff','--binary'])
for relative in subprocess.check_output(['git','-C',str(repo),'ls-files','--others','--exclude-standard'],text=True).splitlines():
    patch+=subprocess.run(['git','diff','--no-index','--binary','--','/dev/null',relative],cwd=repo,stdout=subprocess.PIPE,check=False).stdout
path=r/'artifacts/darling-libsystem-kernel.patch';path.write_bytes(patch)
subprocess.run(['git','-C',str(repo),'apply','--reverse','--check',str(path)],check=True)
PY
