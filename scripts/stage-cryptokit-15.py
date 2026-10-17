#!/usr/bin/env python3
"""Stage untouched Intel CryptoKit from the verified Apple 15.4.1 recovery."""
from pathlib import Path
import fcntl,hashlib,json,plistlib,shutil
root=Path(__file__).resolve().parent.parent;digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
reference=json.loads((root/'artifacts/img4-older-recovery-reference.json').read_text())
assert reference['Apple_chunklist_verification_passed'] and reference['system_version']['ProductVersion']=='15.4.1'
for key in ['recovery_image','chunklist']:assert digest(reference[key])==reference[key+'_sha256'],key
base=root/'runtime/cryptokit-15-native';source_root=root/'runtime/cryptokit-15-reference/macOS Base System';images=[]
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    for parent,name in [('System/Library/PrivateFrameworks','CryptoKitCBridging'),('System/Library/Frameworks','CryptoKit')]:
        source=source_root/parent/(name+'.framework/Versions/A')/name
        assert source.read_bytes()[:8]==bytes.fromhex('cffaedfe07000001')
        framework=base/'frameworks'/(name+'.framework');output=framework/'Versions/A'/name;output.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,output.with_suffix('.pending'));output.with_suffix('.pending').replace(output)
        assert digest(source)==digest(output)
        resources=source.parent/'Resources'
        if resources.exists():shutil.copytree(resources,output.parent/'Resources',dirs_exist_ok=True)
        for path,destination in [(framework/'Versions/Current','A'),(framework/name,'Versions/Current/'+name),(framework/'Resources','Versions/Current/Resources')]:
            if not path.is_symlink():path.symlink_to(destination)
        images.append(dict(provider='/'+parent+'/'+name+'.framework/Versions/A/'+name,original=str(source.relative_to(root)),original_sha256=digest(source),framework=str(output.relative_to(root)),framework_sha256=digest(output),binary_modified=False))
record=dict(images=images,reference='artifacts/img4-older-recovery-reference.json',reference_sha256=digest('artifacts/img4-older-recovery-reference.json'),system_version=reference['system_version'],installed=False,binary_modifications=False,runtime_execution_verified=False,full_CryptoKit_compatibility=False)
(root/'artifacts/cryptokit-15-stage.json').write_text(json.dumps(record,indent=2)+'\n');print('Staged untouched Intel CryptoKit 15.4.1 and C bridge')
