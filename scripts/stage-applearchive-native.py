#!/usr/bin/env python3
"""Select complete pinned original AppleArchive/Swift/Compression images privately."""
from pathlib import Path
import fcntl,hashlib,json,shutil
root=Path(__file__).resolve().parent.parent
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
pins=json.loads((root/'config/cache-image-pins.json').read_text())
targets=['apple-archive-crypto-native','swift-apple-archive-crypto-native','swift-compression-archive-native']
base=root/'runtime/applearchive-native';base.mkdir(exist_ok=True);images=[]
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);pending=base/'libraries.pending'
    if pending.exists():shutil.rmtree(pending)
    pending.mkdir()
    for target in targets:
        pin=pins[target];name=Path(pin['path']).name;report='runtime/rebuilt-'+target+'/reconstruction.json';d=json.loads((root/report).read_text())
        original='runtime/fullsystem-libraries'+pin['path'];source='runtime/rebuilt-'+target+'/'+name
        assert digest(original)==pin['sha256']==d['original_image_sha256'] and digest(source)==d['staged_image_sha256']
        assert not d['modern_adapter'] and not d['backend_call_overrides'] and not d['redirected_imports']
        shutil.copy2(root/source,pending/name)
        images.append(dict(target=target,original=original,original_sha256=digest(original),source=source,source_sha256=digest(source),reconstruction=report,reconstruction_sha256=digest(report),exports=d['exports']))
    previous=base/'libraries.previous';destination=base/'libraries'
    if previous.exists():shutil.rmtree(previous)
    if destination.exists():destination.replace(previous)
    pending.replace(destination)
    if previous.exists():shutil.rmtree(previous)
    d=dict(images=images,libraries=str(destination.relative_to(root)),files={str(p.relative_to(root)):digest(str(p.relative_to(root))) for p in destination.iterdir()},installed=False,backend_overrides=False,archive_processing_verified=False,crypto_streams_verified=False,full_xcode_build_ready=False)
    (root/'artifacts/applearchive-native-stage.json').write_text(json.dumps(d,indent=2)+'\n')
print('Staged three original images; stream execution still requires validation')
