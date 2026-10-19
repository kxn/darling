#!/usr/bin/env python3
"""Install the iOS test dependency using the real Darwin CocoaPods executable."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, runpy, subprocess

root = Path(__file__).resolve().parent.parent
module = runpy.run_path(str(root / 'scripts/metadata-root-name-runtime-profile.py'))
profile = module['profile']()
# Xcode's newer framework overrides are private to its process tree. Ruby
# retains its matched LibreSSL stack in the same Darling runtime.
command = [arg for arg in profile['command'][:-2] if not arg.startswith(('DYLD_LIBRARY_PATH=', 'DYLD_FRAMEWORK_PATH='))] + ['/bin/bash', '-c',
    'cd /Volumes/SystemRoot/workspace/fixtures/iOSCocoaPodsSmoke && pod install --no-repo-update']
command[3] = '120'
log = 'logs/ios-cocoapods-install-metadata-fixed.log'
with (root / log).open('w') as stream:
    result = subprocess.run(command, cwd=root, env=module['environment'](profile), stdout=stream, stderr=subprocess.STDOUT)
text = (root / log).read_text()
digest = lambda path: hashlib.sha256((root / path).read_bytes()).hexdigest()
files = ['fixtures/iOSCocoaPodsSmoke/' + name for name in [
    'Podfile', 'Podfile.lock', 'Pods/Manifest.lock', 'Pods/Pods.xcodeproj/project.pbxproj',
    'iOSCocoaPodsSmoke.xcodeproj/project.pbxproj', 'iOSCocoaPodsSmoke.xcworkspace/contents.xcworkspacedata']]
record = dict(checked_at=datetime.now(timezone.utc).isoformat(), command=command,
              log=log, log_sha256=digest(log), exit_status=result.returncode,
              generated_files={name: digest(name) for name in files if (root / name).exists()},
              verified=result.returncode == 0 and 'Pod installation complete!' in text and all((root / name).is_file() for name in files),
              Xcode_framework_overrides_applied_to_Ruby=False, engine_generated_project=False, full_xcode_build_ready=False)
(root / 'artifacts/ios-cocoapods-install.json').write_text(json.dumps(record, indent=2) + '\n')
print(text[-5000:], end='')
raise SystemExit(0 if record['verified'] else 1)
