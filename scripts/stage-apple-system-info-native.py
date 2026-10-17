#!/usr/bin/env python3
"""Stage the complete reconstructed original Intel AppleSystemInfo and resources."""
from pathlib import Path
import fcntl,hashlib,json,plistlib,shutil,subprocess
root=Path(__file__).resolve().parent.parent
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pins=json.loads((root/'config/cache-image-pins.json').read_text())['apple-system-info-native']
build=root/'runtime/rebuilt-apple-system-info-native';report=json.loads((build/'reconstruction.json').read_text())
assert digest(root/'runtime/fullsystem-libraries'/pins['path'].lstrip('/'))==pins['sha256']==report['original_image_sha256']
assert digest(build/'AppleSystemInfo')==report['staged_image_sha256']
assert report['exports']==29 and not report['redirected_imports'] and not report['backend_call_overrides']
resources=root/'runtime/recovery/macOS Base System/System/Library/PrivateFrameworks/AppleSystemInfo.framework/Versions/A/Resources'
info=plistlib.loads((resources/'Info.plist').read_bytes())
assert info['CFBundleIdentifier']=='com.apple.AppleSystemInfo' and info['CFBundleExecutable']=='AppleSystemInfo'
base=root/'runtime/apple-system-info-native';base.mkdir(exist_ok=True)
stage=base/'frameworks';pending=base/'frameworks.pending';previous=base/'frameworks.previous'
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    for path in [pending,previous]:
        if path.exists():shutil.rmtree(path)
    framework=pending/'AppleSystemInfo.framework';version=framework/'Versions/A';version.mkdir(parents=True)
    shutil.copyfile(build/'AppleSystemInfo',version/'AppleSystemInfo');shutil.copytree(resources,version/'Resources')
    for path,target in [(framework/'Versions/Current','A'),(framework/'AppleSystemInfo','Versions/Current/AppleSystemInfo'),
        (framework/'Resources','Versions/Current/Resources')]:path.symlink_to(target)
    if stage.exists():stage.replace(previous)
    pending.replace(stage)
    if previous.exists():shutil.rmtree(previous)
framework=stage/'AppleSystemInfo.framework';image=framework/'Versions/A/AppleSystemInfo'
record=dict(installed=False,native_execution_verified=False,original=pins,
    framework=str(image.relative_to(root)),framework_sha256=digest(image),
    reconstruction_report=str((build/'reconstruction.json').relative_to(root)),reconstruction_report_sha256=digest(build/'reconstruction.json'),
    original_exports_preserved=29,original_functions_analyzed=report['code_analysis']['function_entries'],
    original_resources={str(p.relative_to(resources)):digest(p) for p in sorted(resources.rglob('*')) if p.is_file()},
    staged_resources={str(p.relative_to(root)):digest(p) for p in sorted((framework/'Versions/A/Resources').rglob('*')) if p.is_file()},
    bundle_identifier=info['CFBundleIdentifier'],resource_source=str(resources.relative_to(root)),
    scope='Original native code and bundle resources; cache pointer/import relocations only. No fake CPU-description getter or source ASI implementation.',
    full_xcode_build_ready=False,signing_ready=False)
(root/'artifacts/apple-system-info-native-stage.json').write_text(json.dumps(record,indent=2)+'\n')
print('Staged original AppleSystemInfo 29 exports, 43 functions and original bundle resources')
