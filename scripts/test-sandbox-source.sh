#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" \
    -c fixtures/hello/sandbox-extension-source.c -o artifacts/sandbox-extension-source.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 \
    -syslibroot runtime/rootfs/usr/libexec/darling -lSystem \
    artifacts/sandbox-extension-source.o -o artifacts/sandbox-extension-source
source_uuid=$(python3 - <<'PY'
from pathlib import Path
import hashlib,json,re,subprocess
r=Path.cwd();digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ref=json.loads((r/'runtime/rebuilt-sandbox-native/reconstruction.json').read_text())
pin=json.loads((r/'config/cache-image-pins.json').read_text())['sandbox-native']
assert digest(r/'runtime/rebuilt-sandbox-native/libsystem_sandbox.dylib')==ref['staged_image_sha256']
assert digest(r/'runtime/fullsystem-libraries/usr/lib/system/libsystem_sandbox.dylib')==ref['original_image_sha256']==pin['sha256']
out=subprocess.check_output(['llvm-dwarfdump-19','--uuid','runtime/sandbox-source/libsystem_sandbox.dylib'],text=True)
print(re.search(r'UUID: ([0-9A-F-]+) \(x86_64\)',out)[1].replace('-','').lower())
PY
)
export LINUXCODE_DARLING_SERVER="$project/runtime/darlingserver-source-build/darlingserver/darlingserver"
export LINUXCODE_LIBXPC="$project/runtime/libxpc-source/libxpc.dylib"
export LINUXCODE_LAUNCHD="$project/runtime/launchd-source/launchd"
export LINUXCODE_LIBSYSTEM_KERNEL="$project/runtime/libsystem-kernel-source/libsystem_kernel.dylib"
export LINUXCODE_QUARANTINE="$project/runtime/quarantine-source/libquarantine.dylib"
export LINUXCODE_SANDBOX="$project/runtime/sandbox-source/libsystem_sandbox.dylib"
workspace=/Volumes/SystemRoot/workspace
timeout -k 5 60 bin/darling shell "$workspace/artifacts/sandbox-extension-source" "$source_uuid" \
    "$workspace/runtime/rebuilt-sandbox-native/libsystem_sandbox.dylib" > logs/sandbox-extension-source.log 2>&1
rg -q '^SANDBOX_SOURCE_LIBRARY_UUID_VERIFIED$' logs/sandbox-extension-source.log
rg -q '^SANDBOX_NATIVE_FOUR_POINTER_CLASSES_AND_FOUR_UINT32_FLAGS_MATCH_OK$' logs/sandbox-extension-source.log
rg -q '^SANDBOX_NATIVE_128_ISSUE_32_UNRESOLVED_32_CONSUME_32_RELEASE_ABI_AND_REAL_MISSING_POLICY_ERRORS_MATCH_OK$' logs/sandbox-extension-source.log
rg -q '^SANDBOX_MAC_POLICY_AND_REAL_POSITIVE_TOKEN_GRANTS_REMAIN_UNIMPLEMENTED$' logs/sandbox-extension-source.log
set +e
env -u LINUXCODE_SANDBOX timeout -k 5 30 bin/darling shell \
    "$workspace/artifacts/sandbox-extension-source" "$source_uuid" \
    "$workspace/runtime/rebuilt-sandbox-native/libsystem_sandbox.dylib" \
    > logs/sandbox-source-packaged-rejection.log 2>&1
rejection=$?
set -e
[[ $rejection == 88 ]]
rg -q '^SOURCE_SANDBOX_LIBRARY_REJECTED$' logs/sandbox-source-packaged-rejection.log
timeout -k 5 45 bin/darling shell /usr/bin/xcodebuild -version > logs/sandbox-source-xcode-version.log 2>&1
rg -q '^Xcode 26.6$' logs/sandbox-source-xcode-version.log
rg -q '^Build version 17F113$' logs/sandbox-source-xcode-version.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess
r=Path.cwd();digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=r/'artifacts/sandbox-source.json';report=json.loads(p.read_text())
assert digest(r/'runtime/sandbox-source/libsystem_sandbox.dylib')==report['library_sha256']
assert digest(r/report['source_configuration']['baseline'])==report['source_configuration']['baseline_sha256']
for path,sha in report['source_files'].items():assert digest(r/path)==sha
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
repo=r/'vendor/darling'
patch=subprocess.check_output(['git','-C',str(repo),'diff','--binary','--','src/sandbox'])
for path in subprocess.check_output(['git','-C',str(repo),'ls-files','--others','--exclude-standard','--','src/sandbox'],text=True).splitlines():
    patch+=subprocess.run(['git','diff','--no-index','--binary','--','/dev/null',path],cwd=repo,stdout=subprocess.PIPE,check=False).stdout
patch_path=r/'artifacts/darling-sandbox-extension.patch';patch_path.write_bytes(patch)
subprocess.run(['git','-C',str(repo),'apply','--reverse','--check',str(patch_path)],check=True)
report.update(verified_at=datetime.now(timezone.utc).isoformat(),runtime_execution_verified=True,
    selected_runtime=selected,native_abi_constants_and_missing_policy_differential_verified=True,
    original_native_image_sha256=digest(r/'runtime/fullsystem-libraries/usr/lib/system/libsystem_sandbox.dylib'),
    reconstructed_native_image_sha256=digest(r/'runtime/rebuilt-sandbox-native/libsystem_sandbox.dylib'),
    test_source_sha256=digest(r/'fixtures/hello/sandbox-extension-source.c'),
    test_binary_sha256=digest(r/'artifacts/sandbox-extension-source'),
    log_sha256=digest(r/'logs/sandbox-extension-source.log'),packaged_library_rejected=True,
    original_xcodebuild_version_verified=True,xcode_version_log_sha256=digest(r/'logs/sandbox-source-xcode-version.log'),
    patch=str(patch_path.relative_to(r)),patch_sha256=digest(patch_path),
    native_issue_comparisons=128,native_unresolved_marker_comparisons=32,
    native_consume_failure_comparisons=32,native_release_failure_comparisons=32,
    sandbox_mac_policy_implemented=False,real_extension_grants_implemented=False,
    native_macos_kernel_behavior_compared=False,full_xcode_build_ready=False,signing_ready=False,
    known_limits=['Missing Sandbox policy is reported as real ENOPOLICY through the MAC syscall, not replaced by a positive grant.',
      'The flag-1 invalid marker is an original native user-space path and grants no access; its C string, allocation size and consume result are compared.',
      'No positive issue/consume/release, target audit-token validation, capability authorization or sandbox policy enforcement is implemented.',
      'Legacy sandbox_init and sandbox_check stubs remain unchanged. Their old success returns are not evidence of enforcement.',
      'Four data objects intentionally change from the old erroneous array/uint64 layout to the verified native pointer/uint32 ABI. Old incorrectly compiled callers are not exhaustively tested.'])
p.write_text(json.dumps(report,indent=2)+'\n')
PY
