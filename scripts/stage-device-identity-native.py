#!/usr/bin/env python3
"""Stage the original Intel DeviceIdentity dependency closure for execution."""
from pathlib import Path
import fcntl,hashlib,json,plistlib,shutil
root=Path(__file__).resolve().parent.parent
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
base=root/'runtime/device-identity-native'
specs=[('device-identity-native','DeviceIdentity',True),('boot-policy-native','libbootpolicy.dylib',False),('image4-device-native','libimage4.dylib',False),('multiverse-support-native','MultiverseSupport',True)]
pins=json.loads((root/'config/cache-image-pins.json').read_text())
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    pending=base/'stage.pending'
    if pending.exists():shutil.rmtree(pending)
    (pending/'frameworks').mkdir(parents=True);(pending/'libraries').mkdir()
    reports={};originals={};resources={}
    for target,name,is_framework in specs:
        pin=pins[target];original='runtime/fullsystem-libraries'+pin['path'];report_name='runtime/rebuilt-'+target+'/reconstruction.json';report=json.loads((root/report_name).read_text())
        source='runtime/rebuilt-'+target+'/'+name
        assert digest(original)==pin['sha256']==report['original_image_sha256']
        assert digest(source)==report['staged_image_sha256']
        assert not report['modern_adapter'] and not report['backend_call_overrides'] and not report['redirected_imports']
        originals[original]=digest(original);reports[report_name]=digest(report_name)
        if is_framework:
            framework=pending/'frameworks'/(name+'.framework');version=framework/'Versions/A';version.mkdir(parents=True)
            shutil.copy2(root/source,version/name)
            resource_name='runtime/recovery/macOS Base System'+str(Path(pin['path']).parent)+'/Resources';resource=root/resource_name
            assert resource.is_dir(),resource_name
            info=plistlib.loads((resource/'Info.plist').read_bytes());assert info['CFBundleExecutable']==name
            shutil.copytree(resource,version/'Resources');resources[name]=resource_name
            for path,destination in [(framework/'Versions/Current','A'),(framework/name,'Versions/Current/'+name),(framework/'Resources','Versions/Current/Resources')]:path.symlink_to(destination)
        else:shutil.copy2(root/source,pending/'libraries'/name)
    alias_reference='artifacts/img4-older-recovery-reference.json';alias=json.loads((root/alias_reference).read_text());alias_path=alias['extracted_libimg4'][0];alias_target=alias['extracted_symlinks'][alias_path]
    import os
    assert os.readlink(root/alias_path)==alias_target=='./libimage4.dylib'
    (pending/'libraries/libimg4.dylib').symlink_to(alias_target)
    for folder in ['frameworks','libraries']:
        selected=base/folder;previous=base/(folder+'.previous')
        if previous.exists():shutil.rmtree(previous)
        if selected.exists():selected.replace(previous)
        (pending/folder).replace(selected)
        if previous.exists():shutil.rmtree(previous)
    pending.rmdir()
    files={str(p.relative_to(root)):digest(str(p.relative_to(root))) for folder in ['frameworks','libraries'] for p in (base/folder).rglob('*') if p.is_file()}
    report_name='runtime/rebuilt-device-identity-native/reconstruction.json';report=json.loads((root/report_name).read_text());original=next(n for n in originals if n.endswith('/DeviceIdentity'))
    symlinks={str(p.relative_to(root)):os.readlink(p) for folder in ['frameworks','libraries'] for p in (base/folder).rglob('*') if p.is_symlink()}
    record=dict(alias_reference=alias_reference,alias_reference_sha256=digest(alias_reference),symlinks=symlinks,original=original,original_sha256=originals[original],originals=originals,reconstruction=report_name,reconstruction_sha256=reports[report_name],files=files,framework_path=str((base/'frameworks').relative_to(root)),libraries_path=str((base/'libraries').relative_to(root)),dependencies={n:sha for n,sha in reports.items() if n!=report_name},original_exports=report['exports'],original_methods=report['objc_metadata']['methods'],backend_overrides=False,original_resources=resources,installed=False,device_attestation_verified=False,native_execution_verified=False)
    (root/'artifacts/device-identity-native-stage.json').write_text(json.dumps(record,indent=2)+'\n')
    print('Staged',len(specs),'original images and original framework resources; execution still unverified')
