#!/usr/bin/env python3
"""Initialize the native directory-helper root in the private guest filesystem."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, subprocess
root = Path(__file__).resolve().parent.parent
digest = lambda p: hashlib.sha256((root / p).read_bytes()).hexdigest()
subprocess.run(['python3', str(root / 'scripts/repair-overlay-var.py')], check=True)
profile = json.loads((root / 'artifacts/uniform-type-identifiers-native-xcode-sandbox-container-nounlink-typed-malloc-simple-log-datavault-user-local-dir-source-libtrace-source-objc-support-showsdks.json').read_text())
environment = os.environ.copy()
for name, item in profile['source_runtime'].items():
    assert digest(item['path']) == item['sha256']; environment[name] = str(root / item['path'])
command = profile['command'][:-2] + ['/bin/bash', '-c',
    'test -L /var && mkdir -p /var/folders && chmod 755 /var/folders && test -d /var/root && ls -ldn /var /var/folders /private/var/folders /var/root']
log = 'logs/native-directory-root-prepare.log'
with (root / log).open('w') as stream:
    result = subprocess.run(command, cwd=root, env=environment, stdout=stream, stderr=subprocess.STDOUT)
text = (root / log).read_text(); print(text)
assert result.returncode == 0 and '/var -> private/var' in text
report = dict(checked_at=datetime.now(timezone.utc).isoformat(), command=command,
    source_runtime=profile['source_runtime'], exit_status=result.returncode,
    log=log, log_sha256=digest(log), diagnostic=text,
    private_root_layout_and_base_directory_verified=True, protected_directory_flags_verified=False)
(root / 'artifacts/native-directory-root-prepare.json').write_text(json.dumps(report, indent=2) + '\n')
