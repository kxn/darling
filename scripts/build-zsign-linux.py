#!/usr/bin/env python3
"""Build the pinned upstream Linux signer privately, without installing it."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, subprocess

root = Path(__file__).resolve().parent.parent
pin = json.loads((root / 'config/zsign-source.json').read_text())
source = root / 'vendor/zsign'
if not source.exists():
    subprocess.run(['git', 'clone', '--no-checkout', pin['repository'], str(source)], check=True)
    subprocess.run(['git', '-C', str(source), 'checkout', '--detach', pin['revision']], check=True)
assert subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip() == pin['revision']
assert not subprocess.check_output(['git', '-C', str(source), 'diff', 'HEAD', '--', 'src', 'build/linux'])
build = root / 'runtime/zsign-linux'
build.mkdir(exist_ok=True)
command = ['make', '-C', str(source / 'build/linux'), '-j8', 'BINDIR=' + str(build)]
log = 'logs/zsign-linux-source-build.log'
with (root / log).open('w') as stream:
    subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=True)
binary = build / 'zsign'
version = subprocess.check_output([str(binary), '--version'], text=True).strip()
digest = lambda path: hashlib.sha256((root / path).read_bytes()).hexdigest()
record = dict(checked_at=datetime.now(timezone.utc).isoformat(), source=pin,
              command=command, binary=str(binary.relative_to(root)), binary_sha256=digest(binary),
              log=log, log_sha256=digest(log), version=version, installed=False,
              Darwin_frontend_integration_verified=False)
(root / 'artifacts/zsign-linux-build.json').write_text(json.dumps(record, indent=2) + '\n')
print('Built pinned Linux zsign:', version)
