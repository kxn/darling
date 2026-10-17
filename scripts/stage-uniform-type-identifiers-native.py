#!/usr/bin/env python3
"""Stage the paired original Intel UTI framework and Swift overlay privately."""
from pathlib import Path
import fcntl, hashlib, json, shutil

root = Path(__file__).resolve().parent.parent
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
pins = json.loads((root / 'config/cache-image-pins.json').read_text())
base = root / 'runtime/uniform-type-identifiers-native'
base.mkdir(exist_ok=True)
records = {}
with (root / 'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    for target, relative in [
        ('uniform-type-identifiers-native', 'frameworks/UniformTypeIdentifiers.framework/Versions/A/UniformTypeIdentifiers'),
        ('swift-uniform-type-identifiers-native', 'libraries/libswiftUniformTypeIdentifiers.dylib'),
    ]:
        pin = pins[target]
        build = root / ('runtime/rebuilt-' + target)
        report = json.loads((build / 'reconstruction.json').read_text())
        source = build / Path(pin['path']).name
        assert digest(root / 'runtime/fullsystem-libraries' / pin['path'].lstrip('/')) == pin['sha256'] == report['original_image_sha256']
        assert digest(source) == report['staged_image_sha256']
        assert len(report['objc_metadata']['classes']) == pin['objc_classes']
        destination = base / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        pending = destination.with_suffix('.pending')
        shutil.copyfile(source, pending)
        pending.replace(destination)
        records[target] = dict(original=pin, path=str(destination.relative_to(root)),
            sha256=digest(destination), reconstruction_report=str((build / 'reconstruction.json').relative_to(root)),
            reconstruction_report_sha256=digest(build / 'reconstruction.json'), exports=report['exports'])
    framework = base / 'frameworks/UniformTypeIdentifiers.framework'
    resources = root / 'runtime/recovery/macOS Base System/System/Library/Frameworks/UniformTypeIdentifiers.framework/Versions/A/Resources'
    shutil.copytree(resources, framework / 'Versions/A/Resources', dirs_exist_ok=True)
    for name, target in [('Versions/Current', 'A'), ('UniformTypeIdentifiers', 'Versions/Current/UniformTypeIdentifiers'), ('Resources', 'Versions/Current/Resources')]:
        link = framework / name
        if not link.is_symlink():
            link.symlink_to(target)

report = dict(installed=False, native_execution_verified=False, images=records,
    resources={str(p.relative_to(root)): digest(p) for p in sorted((framework / 'Versions/A/Resources').rglob('*')) if p.is_file()},
    scope='Original code with cache imports and metadata restored; no substitute UTType layout.',
    full_xcode_build_ready=False, signing_ready=False)
(root / 'artifacts/uniform-type-identifiers-native-stage.json').write_text(json.dumps(report, indent=2) + '\n')
print('Staged original UTI framework and Swift overlay; execution remains unverified')
