#!/usr/bin/env python3
"""Verify native policy decoding and the still-failing original service path."""
# Preserve the newer enabled-launchd checkpoint when invoked historically.
from pathlib import Path as _ls_Path
import json as _ls_json
_ls_state=_ls_Path(__file__).resolve().parent.parent/'artifacts/current-work-state.json'
if _ls_state.exists() and _ls_json.loads(_ls_state.read_text()).get('latest_launchd_sandbox_progress')=='artifacts/launchd-sandbox-progress.json':
    print('Preserving the newer launchd Sandbox checkpoint');raise SystemExit(0)
from pathlib import Path
from datetime import datetime, timezone
import ast, fcntl, hashlib, json, subprocess

root = Path(__file__).resolve().parent.parent
read = lambda n: json.loads((root / n).read_text())
digest = lambda n: hashlib.sha256((root / n).read_bytes()).hexdigest()
evidence = {}
def add(name, sha=None):
    actual = digest(name)
    if sha is not None: assert actual == sha, name
    evidence[name] = actual
def walk(value):
    if isinstance(value, list):
        for item in value: walk(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, str) and isinstance(value.get(key + '_sha256'), str) and (root / item).is_file():
                add(item, value[key + '_sha256'])
            if key == 'sha256':
                for pkey in ['source', 'path']:
                    if pkey + '_sha256' not in value and isinstance(value.get(pkey), str) and (root / value[pkey]).is_file():
                        add(value[pkey], item)
            if isinstance(item, (dict, list)): walk(item)
def report(name):
    d = read(name); add(name); walk(d); return d

profile = __import__('runpy').run_path(str(root / 'scripts/sandbox-policy-vm-server-profile.py'))['profile']()
build = report('artifacts/sandbox-policy-vm-server-build.json')
assert build == profile['source_sandbox_policy_vm']
assert build['engine_called_by_runtime'] and build['baseline_build_output_restored']
assert not build['profile_application_implemented'] and not build['operation_enforcement_implemented']
for name, sha in build['source_files'].items(): add(name, sha)
tables = report('artifacts/native-sandbox-tables.json')
assert len(tables['operation_names']) == 198 and len(tables['filters']) == 105
system = {item['name']: item['value'] for item in tables['filters']['26']['enums']}
assert system['apple-internal'] == 0 and system['sandbox-debug-mode'] == 1
corpus = report('artifacts/native-sandbox-policy-corpus.json')
assert corpus['exit_status'] == 0 and len(corpus['policies']) == 26 and not corpus['policy_applied']
for item in corpus['policies'].values(): add(item['binary'], item['sha256'])
semantic = report('artifacts/native-sandbox-policy-vm-test.json')
parser = report('artifacts/native-sandbox-policy-parser-test.json')
assert semantic['semantic_cases'] == 6034 and not semantic['failures'] and semantic['exit_status'] == 0
assert parser['cases'] == 6488 and not parser['failures'] and parser['exit_status'] == 0
assert parser['valid_original_programs'] == 26 and parser['mutation_safety_cases'] == 3000
assert semantic['ASan_UBSan'] and parser['ASan_UBSan']
upload = report('artifacts/native-sandbox-policy-upload-test.json')
assert upload['runtime_execution_verified'] and upload['checks'] == 216 and upload['uploads'] == 29
assert len(upload['decoded_node_counts']) == 29 and upload['decoded_node_counts'].count(37) == 2
assert not upload['profile_application_implemented']
entrypoints = report('artifacts/sandbox-policy-enforcement-entrypoints.json')
assert entrypoints['selected_launchd_sandbox_macro'] == 0
assert not entrypoints['selected_launchd_imports_sandbox_check']
assert len(entrypoints['source_sandbox_checks']) == 11
for name, sha in entrypoints['evidence'].items(): add(name, sha)
service_name = 'artifacts/fileidtree-service-policy-vm-sandbox-resources-source-dirs-dirhelper-trace-upload-decoded.json'
service = report(service_name)
assert service['debugger_exit_status'] == 0 and service['exit_status'] == -9
assert service['source_sandbox_policy_vm'] == build
trace = (root / service['trace']).read_text()
for marker in ['native_sandbox_compile_return', 'native_sandbox_apply_return  rax=0xffffffff',
               'sandbox_profile_failure Operation not supported', 'exited with code 01']:
    assert marker in trace, marker
assert 'CORESERVICES_TRACE bootstrap_checkin_return' not in trace
for path, sha in service['service_logs'].items(): add(path, sha)
daemon = next(job for job in service['jobs'] if job['name'] == 'coreservicesd')
assert not daemon['binary_modified'] and daemon['source_sha256'] == daemon['selected_sha256']
server_log = 'logs/native-sandbox-policy-coreservices-server.log'
assert 'Sandbox upload decoded: 37 nodes; attachment refused' in (root / server_log).read_text()
add(server_log)

scripts = ['scripts/' + n for n in [
    'build-sandbox-policy-vm-server.py', 'sandbox-policy-vm-server-profile.py',
    'build-native-sandbox-policy-corpus.py', 'extract-native-sandbox-tables.py',
    'test-native-sandbox-policy-vm.py', 'test-native-sandbox-policy-parser.py',
    'test-native-sandbox-policy-upload.py', 'record-native-sandbox-policy-progress.py',
    'probe-fileidtree-service.py', 'dump-native-sandbox-policies.py',
    'quarantine-vfs-runtime-profile.py', 'validate-native-sandbox-policy-checkpoint.py']]
for name in scripts:
    ast.parse((root / name).read_text()); add(name)
for name in ['fixtures/hello/sandbox-policy-vm.cpp', 'fixtures/hello/sandbox-policy-parse.cpp',
             'fixtures/hello/sandbox-policy-upload.c', 'fixtures/hello/sandbox-policy-corpus.c',
             'fixtures/hello/sandbox-policy-dump.c', 'logs/native-sandbox-apply-container-disassembly.log',
             'logs/native-sandbox-fsa-serialize-disassembly.log', 'artifacts/darlingserver-sandbox-policy-source.patch',
             'vendor/sandblaster_26/LICENSE']:
    add(name)
reference_commit = subprocess.check_output(['git', '-C', str(root / 'vendor/sandblaster_26'), 'rev-parse', 'HEAD'], text=True).strip()
assert reference_commit == '3dc6582f7f7d137adaa115f635eb5fc8e8da91f5'
histories = {}
for name in ['artifacts/native-crypto-before-policy-vm-history/manifest.json',
             'artifacts/sandbox-policy-server-input-history/manifest.json',
             'artifacts/sandbox-policy-fixture-correction-history/manifest.json']:
    frozen = read(name); add(name)
    for item in frozen.values(): add(item['archived'], item['sha256'])
    histories[name] = dict(sha256=digest(name), entries=len(frozen))
subprocess.run(['git', '-C', str(root / 'vendor/darlingserver'), 'apply', '--reverse', '--check',
                str(root / 'artifacts/darlingserver-sandbox-policy-source.patch')], check=True)
with (root / 'runtime/session.lock').open('a') as lock: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
assert digest('runtime/darlingserver-source-build/darlingserver/darlingserver') == build['baseline_build_output_sha256']
record = dict(
    checked_at=datetime.now(timezone.utc).isoformat(), goal_status='active', complete=False,
    original_policy_programs=26, native_operation_names=198, native_filter_records=105,
    semantic_cases=6034, malformed_and_mutation_cases=6488, runtime_upload_checks=216,
    runtime_uploads_decoded=29, real_coreservices_profile_decoded=True,
    selected_launchd_compiles_out_sandbox_checks=True,
    candidate_server_started_and_exercised=True,
    original_coreservicesd_modified=False, original_coreservicesd_reached_bootstrap=False,
    original_coreservicesd_exit_status=1, original_coreservicesd_apply_errno='ENOTSUP',
    source_server=build, selected_runtime=profile['source_runtime'],
    native_sandbox_compiler=profile['native_sandbox_compiler'],
    profile_application_implemented=False, operation_enforcement_implemented=False,
    original_project_compilation_started=False, full_xcode_build_ready=False,
    new_full_xcode_build_attempted=False, signing_ready=False, default_entry_promoted=False,
    scope='Pinned Intel standalone policy graph and supported FSA/filter subset; decoded uploads are refused atomically until enforcement exists. Paths require resolved guest identity; no claim of complete Unicode, extension, entitlement, container or all-version compatibility.',
    comparison_limits='Four allow-others cases explicitly test original compiler self-allow prologues; mutated structurally valid programs may be accepted for sanitizer safety checks. No original macOS kernel decision oracle was available.',
    reference=dict(url='https://github.com/chensokolovsky/sandblaster_26', commit=reference_commit,
                   license='BSD-3-Clause', role='Format cross-check; original compiler tables/serializer/source are the semantics evidence'),
    histories=histories, evidence=evidence,
    next_work=[
        'Connect genuine file, mmap/exec, Mach, POSIX IPC, process and sysctl operation checks to the decoded policy; derive contexts from real process/vnode state and preserve fork/exec policy inheritance. Do not return successful application while operations bypass policy.',
        'Enable real launchd Sandbox queries: current DARLING preprocessing sets HAVE_SANDBOX=0 and the selected binary has no sandbox_check import. After enabling, handle query errors and verify global/local/XPC lookup domains before claiming Mach enforcement. Canonicalize real guest file identity, including symlinks and descriptors.',
        'After actual policy attachment/enforcement works, start the unchanged CoreServices daemon, restore volume references and FileCoordination, and resume original xcodebuild through Unity/CocoaPods, archive, signing and export.'])
(root / 'artifacts/native-sandbox-policy-progress.json').write_text(json.dumps(record, indent=2) + '\n')
print('Recorded', len(evidence), 'policy evidence hashes; native daemon attachment/enforcement still incomplete')
