#!/usr/bin/env python3
"""Exercise native sandbox_apply uploads in the privately built real server."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, runpy, subprocess
root = Path(__file__).resolve().parent.parent
m = runpy.run_path(str(root / 'scripts/sandbox-policy-vm-server-profile.py'))
p = m['profile']()
digest = lambda n: hashlib.sha256((root / n).read_bytes()).hexdigest()
build = root / 'runtime/sandbox-policy-upload'
build.mkdir(exist_ok=True)
source = 'fixtures/hello/sandbox-policy-upload.c'
obj, binary = build / 'test.o', build / 'test'
sdk = root / 'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
subprocess.run(['clang-19', '-target', 'x86_64-apple-macos14', '-isysroot', str(sdk), '-O0',
                '-c', str(root / source), '-o', str(obj)], check=True)
subprocess.run(['ld64.lld-19', '-arch', 'x86_64', '-platform_version', 'macos', '14', '14',
                '-syslibroot', str(sdk), '-lSystem', str(obj), '-o', str(binary)], check=True)
corpus = json.loads((root / 'artifacts/native-sandbox-policy-corpus.json').read_text())
guest = '/Volumes/SystemRoot/workspace/'
inputs = {}
for item in corpus['policies'].values():
    assert digest(item['binary']) == item['sha256']
    inputs[item['binary']] = item['sha256']
command = p['command'][:-2] + [guest + str(binary.relative_to(root))] + [guest + name for name in inputs]
server_log = root / 'runtime/state/prefix/private/var/log/dserver.log'
before = server_log.stat().st_size if server_log.exists() else 0
r = subprocess.run(command, env=m['environment'](p), capture_output=True, text=True)
text = r.stdout + r.stderr
log = 'logs/native-sandbox-policy-upload.log'
(root / log).write_text(text)
server_text = server_log.read_bytes()[before:].decode(errors='replace')
server_output = 'logs/native-sandbox-policy-upload-server.log'
(root / server_output).write_text(server_text)
match = re.search(r'SANDBOX_UPLOAD_NATIVE_ABI_AND_ATOMIC_FAILURE_OK checks=(\d+) uploads=(\d+)', text)
decoded = re.findall(r'Sandbox upload decoded: (\d+) nodes; attachment refused', server_text)
record = dict(checked_at=datetime.now(timezone.utc).isoformat(), exit_status=r.returncode,
              command=command, source=source, source_sha256=digest(source),
              binary=str(binary.relative_to(root)), binary_sha256=digest(binary.relative_to(root)),
              log=log, log_sha256=digest(log), server_log=server_output, server_log_sha256=digest(server_output),
              checks=int(match[1]) if match else 0, uploads=int(match[2]) if match else 0,
              decoded_node_counts=list(map(int, decoded)), corpus_inputs=inputs,
              server_build='artifacts/sandbox-policy-vm-server-build.json',
              server_build_sha256=digest('artifacts/sandbox-policy-vm-server-build.json'),
              runtime_execution_verified=r.returncode == 0 and match is not None and len(decoded)==29,
              native_sandbox_compiler=p['native_sandbox_compiler'],
              profile_application_implemented=False, full_xcode_build_ready=False)
(root / 'artifacts/native-sandbox-policy-upload-test.json').write_text(json.dumps(record, indent=2) + '\n')
print(r.returncode, text[-4000:]); print('Server decoded node counts:', decoded)
assert record['runtime_execution_verified'] and record['uploads'] == 29
