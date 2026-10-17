#!/usr/bin/env python3
"""Stage original CryptoKit and its original C bridge as an isolated experiment."""
from pathlib import Path
import fcntl,hashlib,json,shutil
root=Path(__file__).resolve().parent.parent;digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
pins=json.loads((root/'config/cache-image-pins.json').read_text());base=root/'runtime/cryptokit-original-native';images=[]
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    for target in ['cryptokit-cbridging-native-original','cryptokit-native-original']:
        pin=pins[target];name=Path(pin['path']).name;original='runtime/fullsystem-libraries'+pin['path'];source='runtime/rebuilt-'+target+'/'+name;report='runtime/rebuilt-'+target+'/reconstruction.json';d=json.loads((root/report).read_text())
        assert digest(original)==pin['sha256']==d['original_image_sha256'];assert digest(source)==d['staged_image_sha256']
        assert not d['modern_adapter'] and not d['backend_call_overrides'] and not d['redirected_imports']
        framework=base/'frameworks'/(name+'.framework');output=framework/'Versions/A'/name;output.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(root/source,output.with_suffix('.pending'));output.with_suffix('.pending').replace(output)
        for path,destination in [(framework/'Versions/Current','A'),(framework/name,'Versions/Current/'+name)]:
            if not path.is_symlink():path.symlink_to(destination)
        images.append(dict(target=target,provider=pin['path'],original=original,original_sha256=digest(original),source=source,source_sha256=digest(source),reconstruction=report,reconstruction_sha256=digest(report),framework=str(output.relative_to(root)),framework_sha256=digest(output),exports=d['exports']))
record=dict(images=images,installed=False,backend_overrides=False,runtime_execution_verified=False,software_crypto_verified=False,SecureEnclave_verified=False,full_xcode_build_ready=False)
(root/'artifacts/cryptokit-original-stage.json').write_text(json.dumps(record,indent=2)+'\n');print('Staged original CryptoKit + C bridge; runtime ABI and algorithms unverified')
