#!/usr/bin/env python3
"""Sign the actual Xcode product, independently verify hashes, reject tampering."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, runpy, shutil, subprocess, tempfile

root = Path(__file__).resolve().parent.parent
build = json.loads((root / 'artifacts/zsign-linux-build.json').read_text())
binary = root / build['binary']
assert hashlib.sha256(binary.read_bytes()).hexdigest() == build['binary_sha256']
verify = runpy.run_path(str(root / 'scripts/verify-adhoc-bundle.py'))['verify']
work = Path(tempfile.mkdtemp(prefix='zsign-adhoc-', dir=root / 'runtime'))
app = work / 'iOSCocoaPodsSmoke.app'
shutil.copytree(root / 'runtime/ios-cocoapods-build/DerivedData/Build/Products/Debug-iphoneos/iOSCocoaPodsSmoke.app', app)
(app / 'Sample.bin').write_bytes(bytes(range(256)) * 4)
log = work / 'sign.log'
command = [str(binary), '-a', '-f', str(app)]
with log.open('w') as stream:
    result = subprocess.run(command, cwd=work, stdout=stream, stderr=subprocess.STDOUT)
assert result.returncode == 0
verified = verify(app)
rejections = []
def reject(name, path, replacement):
    previous = path.read_bytes() if path.exists() else None
    try:
        path.write_bytes(replacement)
        try: verify(app)
        except (AssertionError, ValueError): rejections.append(name)
        else: raise AssertionError('Accepted tampering: ' + name)
    finally:
        if previous is None: path.unlink()
        else: path.write_bytes(previous)
executable = app / 'iOSCocoaPodsSmoke'
data = bytearray(executable.read_bytes()); data[0x4000] ^= 1
reject('code-page', executable, data)
import plistlib
info = plistlib.loads((app / 'Info.plist').read_bytes()); info['CFBundleName'] += '-changed'
reject('valid-modified-Info.plist', app / 'Info.plist', plistlib.dumps(info))
reject('sealed-resource', app / 'Sample.bin', b'changed')
reject('unsigned-added-resource', app / 'Added.bin', b'not sealed')
verify(app)
record = dict(checked_at=datetime.now(timezone.utc).isoformat(), command=command,
    build=build, log=str(log.relative_to(root)), log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),
    application=str(app.relative_to(root)), signature_checks=verified, rejected_tampering=rejections,
    verified=len(rejections) == 4, original_codesign_verify_executed=False,
    provisioned_device_signing_verified=False, xcodebuild_signing_step_integrated=False,
    native_original_frontend_preserved=False)
(root / 'artifacts/zsign-adhoc-test.json').write_text(json.dumps(record, indent=2) + '\n')
print('ZSIGN_REAL_XCODE_IOS_APP_ADHOC_HASHES_AND_FOUR_TAMPER_REJECTIONS_OK')
