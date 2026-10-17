#!/usr/bin/env python3
"""Install the unchanged recovery CoreTypes bundle into the private guest overlay."""
from pathlib import Path
from datetime import datetime, timezone
import fcntl, hashlib, json, os, plistlib, shutil
root = Path(__file__).resolve().parent.parent
source = root / 'runtime/recovery/macOS Base System/System/Library/CoreServices/CoreTypes.bundle'
target = root / 'runtime/state/prefix/System/Library/CoreServices/CoreTypes.bundle'
def manifest(base):
    result = {}
    for path in sorted(base.rglob('*')):
        key = str(path.relative_to(base))
        if path.is_symlink(): result[key] = dict(link=os.readlink(path))
        elif path.is_file(): result[key] = dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), size=path.stat().st_size)
    return result
info = plistlib.loads((source / 'Contents/Info.plist').read_bytes())
assert info['CFBundleIdentifier'] == 'com.apple.coretypes'
assert len(info['UTExportedTypeDeclarations']) == 761 and len(info['UTImportedTypeDeclarations']) == 440
expected = manifest(source)
with (root / 'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    if target.exists(): assert manifest(target) == expected
    else:
        pending = target.with_name(target.name + '.pending')
        assert not pending.exists()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, pending, symlinks=True)
        assert manifest(pending) == expected
        pending.rename(target)
report = dict(checked_at=datetime.now(timezone.utc).isoformat(), source=str(source.relative_to(root)),
    target=str(target.relative_to(root)), files=expected, unchanged_resources=True,
    exported_type_declarations=761, imported_type_declarations=440,
    runtime_database_registration_verified=False,
    scope='Genuine unmodified local recovery resources. Presence and hash equality do not prove LaunchServices registration or queries.')
(root / 'artifacts/coretypes-resources-stage.json').write_text(json.dumps(report, indent=2) + '\n')
print('Staged unchanged CoreTypes bundle:', len(expected), 'files/links, 761 exported + 440 imported declarations')
