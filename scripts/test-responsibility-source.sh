#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
unset LINUXCODE_SANDBOX
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" \
    -c fixtures/hello/responsibility-source.c -o artifacts/responsibility-source.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 \
    -syslibroot runtime/rootfs/usr/libexec/darling -lSystem \
    artifacts/responsibility-source.o -o artifacts/responsibility-source
source_uuid=$(python3 - <<'PY'
from pathlib import Path
import hashlib,json,re,subprocess
r=Path.cwd();digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ref=json.loads((r/'runtime/rebuilt-quarantine-native/reconstruction.json').read_text())
pin=json.loads((r/'config/cache-image-pins.json').read_text())['quarantine-native']
assert digest(r/'runtime/rebuilt-quarantine-native/libquarantine.dylib')==ref['staged_image_sha256']
assert digest(r/'runtime/fullsystem-libraries/usr/lib/system/libquarantine.dylib')==ref['original_image_sha256']==pin['sha256']
text=subprocess.check_output(['llvm-dwarfdump-19','--uuid','runtime/quarantine-source/libquarantine.dylib'],text=True)
print(re.search(r'UUID: ([0-9A-F-]+) \(x86_64\)',text)[1].replace('-','').lower())
PY
)
export LINUXCODE_DARLING_SERVER="$project/runtime/darlingserver-source-build/darlingserver/darlingserver"
export LINUXCODE_LIBXPC="$project/runtime/libxpc-source/libxpc.dylib"
export LINUXCODE_LAUNCHD="$project/runtime/launchd-source/launchd"
export LINUXCODE_LIBSYSTEM_KERNEL="$project/runtime/libsystem-kernel-source/libsystem_kernel.dylib"
export LINUXCODE_QUARANTINE="$project/runtime/quarantine-source/libquarantine.dylib"
workspace=/Volumes/SystemRoot/workspace
timeout -k 5 60 bin/darling shell "$workspace/artifacts/responsibility-source" "$source_uuid" \
    "$workspace/runtime/rebuilt-quarantine-native/libquarantine.dylib" > logs/responsibility-source.log 2>&1
for marker in \
    RESPONSIBILITY_SOURCE_QUARANTINE_LOADED_UUID_VERIFIED \
    RESPONSIBILITY_NATIVE_ATTRIBUTE_32_ROUNDTRIPS_CROSS_GETTERS_FLAGS_AND_ERRORS_MATCH_OK \
    RESPONSIBILITY_REAL_FORK_SPAWN_DISCLAIM_GRANDCHILD_INHERITANCE_AND_NATIVE_QUERY_OK \
    RESPONSIBILITY_REAL_FAILED_SETEXEC_PIPE_ROLLBACK_SUCCESSFUL_SETEXEC_AND_BAD_POINTER_ERRORS_OK; do
    rg -q "^${marker}$" logs/responsibility-source.log
done
set +e
env -u LINUXCODE_QUARANTINE timeout -k 5 30 bin/darling shell \
    "$workspace/artifacts/responsibility-source" "$source_uuid" \
    "$workspace/runtime/rebuilt-quarantine-native/libquarantine.dylib" \
    > logs/responsibility-source-packaged-rejection.log 2>&1
rejection=$?
set -e
[[ $rejection == 88 ]]
rg -q '^SOURCE_RESPONSIBILITY_LIBRARY_REJECTED$' logs/responsibility-source-packaged-rejection.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess
r=Path.cwd();digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
qpath=r/'artifacts/quarantine-source.json';q=json.loads(qpath.read_text())
k=json.loads((r/'artifacts/libsystem-kernel-source.json').read_text())
assert digest(r/'runtime/quarantine-source/libquarantine.dylib')==q['library_sha256']
assert digest(r/'runtime/libsystem-kernel-source/libsystem_kernel.dylib')==q['source_kernel_sha256']==k['binary_sha256']
for path,sha in q['source_files'].items():assert digest(r/path)==sha
for source in k['sources']:assert digest(r/source['source'])==source['sha256']
for relative,value in [(q['source_configuration']['baseline'],q['source_configuration']['baseline_sha256']),
                       (k['source_configuration']['baseline'],k['source_configuration']['baseline_sha256'])]:
    assert digest(r/relative)==value
selected={key:dict(path=value,sha256=digest(r/value)) for key,value in {
    'darlingserver':'runtime/darlingserver-source-build/darlingserver/darlingserver',
    'libxpc':'runtime/libxpc-source/libxpc.dylib','launchd':'runtime/launchd-source/launchd',
    'libsystem_kernel':'runtime/libsystem-kernel-source/libsystem_kernel.dylib',
    'quarantine':'runtime/quarantine-source/libquarantine.dylib'}.items()}
# Confirm the complete private root contains exactly the selected components.
base=r/'runtime/quarantine-source/darling-root'
for name,relative in {'libxpc':'usr/lib/system/libxpc.dylib','launchd':'sbin/launchd',
                      'libsystem_kernel':'usr/lib/system/libsystem_kernel.dylib',
                      'quarantine':'usr/lib/system/libquarantine.dylib'}.items():
    assert digest(base/relative)==selected[name]['sha256']
q.update(runtime_execution_verified=True,verified_at=datetime.now(timezone.utc).isoformat(),
         selected_spawn_responsibility_verified=True)
qpath.write_text(json.dumps(q,indent=2)+'\n')
patches={}
for relative,scope,name in [('vendor/darling','src/quarantine','darling-quarantine-responsibility.patch'),
                             ('vendor/darling/src/external/xnu',None,'darling-libsystem-kernel.patch'),
                             ('vendor/darlingserver',None,'darlingserver-responsibility.patch')]:
    repo=r/relative;pathspec=['--',scope] if scope else []
    patch=subprocess.check_output(['git','-C',str(repo),'diff','--binary',*pathspec])
    for path in subprocess.check_output(['git','-C',str(repo),'ls-files','--others','--exclude-standard',*pathspec],text=True).splitlines():
        patch+=subprocess.run(['git','diff','--no-index','--binary','--','/dev/null',path],cwd=repo,stdout=subprocess.PIPE,check=False).stdout
    path=r/'artifacts'/name;path.write_bytes(patch)
    subprocess.run(['git','-C',str(repo),'apply','--reverse','--check',str(path)],check=True)
    patches[str(path.relative_to(r))]=digest(path)
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),installed=False,full_darling_rebuild=False,
    full_xcode_build_ready=False,signing_ready=False,selected_runtime=selected,
    source_files=q['source_files'],patches=patches,
    test_source_sha256=digest(r/'fixtures/hello/responsibility-source.c'),
    test_binary_sha256=digest(r/'artifacts/responsibility-source'),
    log_sha256=digest(r/'logs/responsibility-source.log'),
    rejection_log_sha256=digest(r/'logs/responsibility-source-packaged-rejection.log'),
    native_reference_original_sha256=digest(r/'runtime/fullsystem-libraries/usr/lib/system/libquarantine.dylib'),
    native_reference_reconstructed_sha256=digest(r/'runtime/rebuilt-quarantine-native/libquarantine.dylib'),
    attribute_roundtrips_compared_with_actual_native_code=32,thread_storage_lifecycles=8,
    real_fork_spawn_disclaim_and_grandchild_inheritance_verified=True,
    responsible_unique_id_matches_actual_libproc_for_self_responsible_children=True,
    native_query_machine_code_uses_same_actual_kernel_backend=True,
    failed_setexec_after_real_linux_exec_failure_preserves_old_responsibility=True,
    successful_setexec_and_later_plain_exec_preserve_correct_responsibility=True,
    invalid_pointer_policy_opcode_and_nonexistent_pid_errors_verified=True,
    packaged_quarantine_rejected=True,native_macos_kernel_behavior_compared=False,
    known_limits=[
      'Selected process attribution only; no macOS TCC consent/enforcement, entitlements, other MAC policies or complete Quarantine state.',
      'Only version-1 24-byte Quarantine spawn records with the disclaim flag and no other policy data are executed; unsupported fields fail explicitly.',
      'The source APIs preserve native per-thread borrowed-buffer semantics; attribute payload lifetime ends when its owner thread exits.',
      'Server records retain responsible PID, birth-based libproc-compatible unique ID and registry generation; forced PID reuse was not tested.',
      'Default attribution is inherited, with a self-responsible root. Native macOS kernel, launch-service attribution heuristics and caller-based overrides are not compared or implemented.',
      'Existing libproc query for PID 1 fails while reading nonexistent parent PID 0; actual self-responsible child IDs are compared with successful libproc calls.',
      'ELF exec success follows the existing Darling checkout behavior that removes non-Darling processes; responsibility queries for those processes are unavailable.'])
(r/'artifacts/responsibility-source.json').write_text(json.dumps(report,indent=2)+'\n')
PY
