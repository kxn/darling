#!/usr/bin/env python3
"""Build and exercise the actual shared FSEvents source under ASan/UBSan."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, subprocess

root = Path(__file__).resolve().parent.parent
source = 'fixtures/hello/fsevents-journal-linux.cpp'
backend = 'vendor/darlingserver/src/fsevents-journal.cpp'
header = 'vendor/darlingserver/internal-include/darlingserver/fsevents-journal.hpp'
binary = 'runtime/fsevents-journal-linux-test'
command = ['g++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror', '-Wno-misleading-indentation',
           '-pthread', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
           '-Ivendor/darlingserver/internal-include', source, backend, '-o', binary]
subprocess.run(command, cwd=root, check=True)
log = 'logs/fsevents-journal-linux-repro-test.log'
with (root / log).open('w') as stream:
    result = subprocess.run([str(root / binary)], cwd=root, stdout=stream, stderr=subprocess.STDOUT)
text = (root / log).read_text()
checks = re.findall(r'FSEVENTS_SHARED_JOURNAL_LINUX_OK checks=(\d+)', text)
digest = lambda path: hashlib.sha256((root / path).read_bytes()).hexdigest()
record = dict(checked_at=datetime.now(timezone.utc).isoformat(), command=command,
              sources={name: digest(name) for name in [source, backend, header]},
              binary=binary, binary_sha256=digest(binary), log=log, log_sha256=digest(log),
              exit_status=result.returncode, checks=int(checks[0]) if checks else 0,
              ASan_UBSan=True, verified=result.returncode == 0 and len(checks) == 1)
(root / 'artifacts/fsevents-journal-linux-test.json').write_text(json.dumps(record, indent=2) + '\n')
print(text, end='')
raise SystemExit(0 if record['verified'] else 1)
