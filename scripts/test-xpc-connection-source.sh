#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
# These explicitly use the packaged backend and retain its damaged-guard test.
bash scripts/test-xpc-rich-error.sh > logs/xpc-source-legacy-rich-error-driver.log 2>&1
bash scripts/test-xpc-connection-compat.sh > logs/xpc-source-legacy-connection-driver.log 2>&1
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -fblocks \
    -c fixtures/hello/xpc-connection-source.c -o artifacts/xpc-connection-source.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 \
    -syslibroot runtime/rootfs/usr/libexec/darling -lSystem \
    artifacts/xpc-connection-source.o -o artifacts/xpc-connection-source
source_uuid=$(python3 - <<'PY'
from pathlib import Path
import re,subprocess,hashlib,json
p=Path('runtime/libxpc-source/libxpc.dylib')
assert hashlib.sha256(p.read_bytes()).hexdigest()==json.loads(Path('artifacts/libxpc-source.json').read_text())['library_sha256']
s=subprocess.check_output(['llvm-dwarfdump-19','--uuid',str(p)],text=True)
print(re.search(r'UUID: ([0-9A-F-]+) \(x86_64\)',s)[1].replace('-','').lower())
PY
)
export LINUXCODE_DARLING_SERVER="$project/runtime/darlingserver-source-build/darlingserver/darlingserver"
export LINUXCODE_LIBXPC="$project/runtime/libxpc-source/libxpc.dylib"
export LINUXCODE_LAUNCHD="$project/runtime/launchd-source/launchd"
export LINUXCODE_LIBSYSTEM_KERNEL="$project/runtime/libsystem-kernel-source/libsystem_kernel.dylib"
export LINUXCODE_QUARANTINE="$project/runtime/quarantine-source/libquarantine.dylib"
export LINUXCODE_SANDBOX="$project/runtime/sandbox-source/libsystem_sandbox.dylib"
workspace=/Volumes/SystemRoot/workspace
for mode in direct delegated bad-legacy-guard; do
    case "$mode" in
        direct) api=/usr/lib/system/libxpc.dylib ;;
        delegated) api="$workspace/runtime/native-library-stage/libDarlingXPCRichError.dylib" ;;
        bad-legacy-guard) api="$workspace/runtime/xpc-rich-error/bad-connection-guard/libDarlingXPCRichError.dylib" ;;
    esac
    timeout -k 5 45 bin/darling shell "$workspace/artifacts/xpc-connection-source" "$api" "$source_uuid" \
        > "logs/xpc-connection-source-${mode}.log" 2>&1
    rg -q '^SOURCE_XPC_8_CONCURRENT_READERS_OBSERVE_REAL_INVALIDATION_AND_32_OWNED_REASON_LIFECYCLES_OK$' "logs/xpc-connection-source-${mode}.log"
    rg -q '^SOURCE_XPC_PEER_SIGNING_REQUIREMENT_RETURNS_UNSUPPORTED_WITHOUT_CONNECTION_MUTATION_OK$' "logs/xpc-connection-source-${mode}.log"
done
set +e
env -u LINUXCODE_DARLING_SERVER -u LINUXCODE_LIBXPC -u LINUXCODE_LAUNCHD \
    -u LINUXCODE_LIBSYSTEM_KERNEL -u LINUXCODE_QUARANTINE -u LINUXCODE_SANDBOX \
    timeout -k 5 30 bin/darling shell "$workspace/artifacts/xpc-connection-source" \
    /usr/lib/system/libxpc.dylib "$source_uuid" > logs/xpc-connection-source-packaged-rejection.log 2>&1
rejection=$?
set -e
[[ $rejection == 88 ]]
rg -q '^SOURCE_CONNECTION_BACKEND_UUID_REJECTED$' logs/xpc-connection-source-packaged-rejection.log
timeout -k 5 45 bin/darling shell /usr/bin/xcodebuild -version > logs/xpc-connection-source-xcode-version.log 2>&1
rg -q '^Xcode 26.6$' logs/xpc-connection-source-xcode-version.log
rg -q '^Build version 17F113$' logs/xpc-connection-source-xcode-version.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess
r=Path.cwd();digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
xp=r/'artifacts/libxpc-source.json';x=json.loads(xp.read_text())
assert digest(r/'runtime/libxpc-source/libxpc.dylib')==x['library_sha256']
for path,sha in x['source_files'].items():assert digest(r/'vendor/darling/src/external/libxpc'/path)==sha
for path,sha in x['modified_files'].items():assert digest(r/'vendor/darling/src/external/libxpc'/path)==sha
helper=json.loads((r/'artifacts/xpc-rich-error-compat.json').read_text())
assert helper['damaged_connection_runtime_guard_rejected'] and helper['selected_error_api_execution_verified']
assert digest(r/'runtime/native-library-stage/libDarlingXPCRichError.dylib')==helper['library_sha256']
assert digest(r/'scripts/xpc-rich-error-compat.m')==helper['source_compatibility_sha256']
selected={name:dict(path=path,sha256=digest(r/path)) for name,path in {
    'darlingserver':'runtime/darlingserver-source-build/darlingserver/darlingserver',
    'libxpc':'runtime/libxpc-source/libxpc.dylib','launchd':'runtime/launchd-source/launchd',
    'libsystem_kernel':'runtime/libsystem-kernel-source/libsystem_kernel.dylib',
    'quarantine':'runtime/quarantine-source/libquarantine.dylib',
    'sandbox':'runtime/sandbox-source/libsystem_sandbox.dylib'}.items()}
for name,path in {'libxpc':'usr/lib/system/libxpc.dylib','launchd':'sbin/launchd',
                   'libsystem_kernel':'usr/lib/system/libsystem_kernel.dylib',
                   'quarantine':'usr/lib/system/libquarantine.dylib','sandbox':'usr/lib/system/libsystem_sandbox.dylib'}.items():
    assert digest(r/'runtime/sandbox-source/darling-root'/path)==selected[name]['sha256']
logs=['logs/xpc-connection-source-'+mode+'.log' for mode in ['direct','delegated','bad-legacy-guard']]
logs+=['logs/xpc-connection-source-packaged-rejection.log','logs/xpc-bad-connection-guard.log',
       'logs/xpc-connection-compat.log','logs/xpc-rich-error-execute.log','logs/xpc-connection-source-xcode-version.log']
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),installed=False,full_darling_rebuild=False,
    selected_runtime=selected,source_libxpc_sha256=x['library_sha256'],adapter_sha256=helper['library_sha256'],
    damaged_legacy_guard_adapter_sha256=digest(r/'runtime/xpc-rich-error/bad-connection-guard/libDarlingXPCRichError.dylib'),
    damaged_legacy_guard_header_sha256=digest(r/'runtime/xpc-rich-error/bad-connection-guard/connection-backend.h'),
    test_source_sha256=digest(r/'fixtures/hello/xpc-connection-source.c'),test_binary_sha256=digest(r/'artifacts/xpc-connection-source'),
    source_files=x['modified_files'],logs={p:digest(r/p) for p in logs},concurrent_readers_per_mode=8,
    actual_cancel_lifecycles_per_mode=33,source_direct_and_adapter_delegation_verified=True,
    atomic_state_published_before_actual_invalid_event=True,owned_independent_reason_buffers_verified=True,
    damaged_legacy_guard_still_rejects_packaged_backend=True,
    source_public_api_delegation_does_not_read_legacy_layout=True,
    source_api_still_works_when_adapter_legacy_fallback_uuid_is_damaged=True,
    packaged_backend_uuid_rejected=True,peer_message_signature_enforcement_implemented=False,
    original_xcodebuild_version_verified=True,full_xcode_build_ready=False,signing_ready=False,
    known_limits=['Descriptions expose the actual Darling cancellation state; detailed modern invalidation codes and peer-signature enforcement remain unsupported.',
       'Raw-layout fallback is still restricted to the pinned packaged binary. Source delegation uses only public SPIs owned by the actual connection backend.',
       'No complete XPC service/session/peer verification compatibility or original project build/archive/signing success claim.'])
(r/'artifacts/xpc-connection-source.json').write_text(json.dumps(report,indent=2)+'\n')
x.update(selected_connection_invalidation_execution_verified=True,source_connection_api_test='artifacts/xpc-connection-source.json')
xp.write_text(json.dumps(x,indent=2)+'\n')
helper.update(source_connection_delegation_execution_verified=True,source_connection_api_test='artifacts/xpc-connection-source.json')
(r/'artifacts/xpc-rich-error-compat.json').write_text(json.dumps(helper,indent=2)+'\n')
repo=r/'vendor/darling/src/external/libxpc';patch=subprocess.check_output(['git','-C',str(repo),'diff','--binary'])
for path in subprocess.check_output(['git','-C',str(repo),'ls-files','--others','--exclude-standard'],text=True).splitlines():
    patch+=subprocess.run(['git','diff','--no-index','--binary','--','/dev/null',path],cwd=repo,stdout=subprocess.PIPE,check=False).stdout
patch_path=r/'artifacts/darling-libxpc-shmem.patch';patch_path.write_bytes(patch)
subprocess.run(['git','-C',str(repo),'apply','--reverse','--check',str(patch_path)],check=True)
PY
