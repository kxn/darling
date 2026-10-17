#!/usr/bin/env python3
"""Compile the standalone policy engine into a private server candidate.

This build does not enable profile attachment: the operation hooks are not yet
connected. Preserve the older server used by all validated runtime profiles.
"""
from pathlib import Path
import datetime
import fcntl
import hashlib
import json
import runpy
import shutil
import subprocess

root = Path(__file__).resolve().parent.parent
parent = runpy.run_path(str(root / 'scripts/sandbox-compiler-resources-profile.py'))['profile']()
digest = lambda path: hashlib.sha256((root / path).read_bytes()).hexdigest()
base = Path('runtime/darlingserver-source-build/darlingserver/darlingserver')
build = root / 'runtime/sandbox-policy-vm-server'
build.mkdir(exist_ok=True)
target = build / 'darlingserver'
expected_baseline = 'ae78babd377dd542788f321752b11e9dea6413ee49d1009f00df825fdd9efd6b'
command = ['cmake', '--build', str(root / 'runtime/darlingserver-source-build'),
           '--target', 'darlingserver', '-j', '8']
log = root / 'logs/sandbox-policy-vm-server-build.log'
with (root / 'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    assert digest(base) == expected_baseline
    backup = build / 'baseline-build-output'
    shutil.copy2(root / base, backup)
    try:
        (root / base).unlink()
        with log.open('w') as output:
            subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, check=True)
        compiled_sha = digest(base)
        pending = target.with_suffix('.pending')
        shutil.copy2(root / base, pending)
        pending.replace(target)
    finally:
        restored = (root / base).with_suffix('.restore')
        shutil.copy2(backup, restored)
        restored.replace(root / base)
    assert digest(base) == expected_baseline
files = ['vendor/darlingserver/' + n for n in [
    'CMakeLists.txt', 'src/call.cpp', 'src/process.cpp',
    'internal-include/darlingserver/process.hpp', 'duct-tape/src/task.c',
    'duct-tape/include/darlingserver/duct-tape.h', 'scripts/generate-rpc-wrappers.py',
    'src/sandbox-policy.cpp', 'src/sandbox-operation-names.inc',
    'internal-include/darlingserver/sandbox-policy.hpp']]
selected = {k: dict(v) for k, v in parent['source_runtime'].items()}
selected['LINUXCODE_DARLING_SERVER'] = {
    'path': str(target.relative_to(root)), 'sha256': digest(target.relative_to(root))}
report = {
    'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'command': command, 'log': str(log.relative_to(root)),
    'log_sha256': digest(log.relative_to(root)),
    'server': str(target.relative_to(root)), 'server_sha256': compiled_sha,
    'compilation_output_path': str(base),
    'baseline_build_output_restored': True,
    'baseline_build_output_sha256': expected_baseline,
    'source_files': {n: digest(n) for n in files},
    'previous_source_runtime': parent['source_runtime'], 'source_runtime': selected,
    'source_commit': subprocess.check_output(
        ['git', '-C', str(root / 'vendor/darlingserver'), 'rev-parse', 'HEAD'], text=True).strip(),
    'engine_compiled_in_server_target': True,
    'engine_called_by_runtime': True,
    'native_profile_upload_decoding_implemented': True,
    'profile_application_implemented': False,
    'operation_enforcement_implemented': False,
    'runtime_execution_verified': False,
    'full_xcode_build_ready': False,
}
(root / 'artifacts/sandbox-policy-vm-server-build.json').write_text(json.dumps(report, indent=2) + '\n')
print('Private server compiled; baseline restored; policy application remains disabled')
