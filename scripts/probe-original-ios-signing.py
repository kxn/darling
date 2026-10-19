#!/usr/bin/env python3
"""Probe genuine codesign on a private copy; never equate wrapper exit with signing."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, re, runpy, shlex, shutil, subprocess, tempfile

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument('--runtime-profile', default='scripts/xcode-tool-dispatch-runtime-profile.py')
args = parser.parse_args()
module = runpy.run_path(str(root / args.runtime_profile))
profile = module['profile']()
folder = Path(tempfile.mkdtemp(prefix='ios-signing-', dir=root / 'runtime'))
app = folder / 'iOSCocoaPodsSmoke.app'
shutil.copytree(root / 'runtime/ios-cocoapods-build/DerivedData/Build/Products/Debug-iphoneos/iOSCocoaPodsSmoke.app', app)
guest_app = shlex.quote('/Volumes/SystemRoot/workspace/' + str(app.relative_to(root)))
script = folder / 'sign.sh'
script.write_text('''#!/bin/bash
set +e
/usr/bin/codesign --force --sign - --timestamp=none ''' + guest_app + '''
status=$?
printf 'ORIGINAL_ADHOC_CODESIGN_STATUS %s\\n' "$status"
if [ "$status" -ne 0 ]; then exit "$status"; fi
/usr/bin/codesign --verify --strict --verbose=2 ''' + guest_app + '''
status=$?
printf 'ORIGINAL_ADHOC_CODESIGN_VERIFY_STATUS %s\\n' "$status"
exit "$status"
''')
command = profile['command'][:-2] + ['/bin/bash', '/Volumes/SystemRoot/workspace/' + str(script.relative_to(root))]
command[3] = '120'
log = folder / 'probe.log'
with log.open('w') as stream:
    result = subprocess.run(command, env=module['environment'](profile), cwd=root, stdout=stream, stderr=subprocess.STDOUT)
text = log.read_text()
digest = lambda path: hashlib.sha256((root / path).read_bytes()).hexdigest()
tool = 'runtime/recovery/macOS Base System/usr/bin/codesign'
entry = 'runtime/state/prefix/usr/bin/codesign'
record = dict(checked_at=datetime.now(timezone.utc).isoformat(), command=command,
    source_runtime=profile['source_runtime'], original_codesign=tool, original_codesign_sha256=digest(tool),
    entrypoint=entry, entrypoint_sha256=digest(entry), script=str(script.relative_to(root)), script_sha256=digest(script),
    log=str(log.relative_to(root)), log_sha256=digest(log), wrapper_exit_status=result.returncode,
    native_sign_status=re.findall(r'^ORIGINAL_ADHOC_CODESIGN_STATUS (\d+)$', text, re.M),
    native_verify_status=re.findall(r'^ORIGINAL_ADHOC_CODESIGN_VERIFY_STATUS (\d+)$', text, re.M),
    adhoc_signing_verified=result.returncode == 0 and '\nORIGINAL_ADHOC_CODESIGN_STATUS 0\n' in text and '\nORIGINAL_ADHOC_CODESIGN_VERIFY_STATUS 0\n' in text,
    provisioned_device_signing_verified=False, full_goal_complete=False)
report = root / 'artifacts/original-ios-adhoc-signing-probe.json'
if report.exists():
    prior = hashlib.sha256(report.read_bytes()).hexdigest()
    archive = root / 'artifacts/ios-signing-probe-history' / prior
    archive.mkdir(parents=True, exist_ok=True)
    shutil.copy2(report, archive / 'report.json')
report.write_text(json.dumps(record, indent=2) + '\n')
print(text[-6000:], end='')
raise SystemExit(0 if record['adhoc_signing_verified'] else 1)
