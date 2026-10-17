#!/usr/bin/env python3
"""Publish a private original Cryptex/AuthInstall/crypto dependency selection."""
from pathlib import Path
import fcntl,hashlib,json,os,plistlib,shutil
root=Path(__file__).resolve().parent.parent;digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
specs=[('cryptex-device-native','libcryptex.dylib'),('cryptex-core-device-native','libcryptex_core.dylib'),('cryptex-interface-device-native','libcryptex_interface.dylib'),('auth-install-device-native','libauthinstall.dylib'),('crypto42-device-native','libcrypto.42.dylib'),('trust-evaluation-crypto42-native','TrustEvaluationAgent'),('swift-system-foundation-cryptex-native','libswiftSystem_Foundation.dylib')]
pins=json.loads((root/'config/cache-image-pins.json').read_text());base=root/'runtime/cryptex-native';base.mkdir(exist_ok=True)
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);pending=base/'stage.pending'
 if pending.exists():shutil.rmtree(pending)
 (pending/'libraries').mkdir(parents=True);(pending/'frameworks').mkdir()
 images=[]
 for target,name in specs:
  report_name='runtime/rebuilt-'+target+'/reconstruction.json';report=json.loads((root/report_name).read_text());original='runtime/fullsystem-libraries'+pins[target]['path'];source='runtime/rebuilt-'+target+'/'+name
  assert digest(original)==pins[target]['sha256']==report['original_image_sha256']
  assert digest(source)==report['staged_image_sha256'] and not report['modern_adapter'] and not report['backend_call_overrides'] and not report['redirected_imports']
  if name=='TrustEvaluationAgent':
   framework=pending/'frameworks/TrustEvaluationAgent.framework';version=framework/'Versions/A';version.mkdir(parents=True);destination=version/name
   resource=root/'runtime/recovery/macOS Base System/System/Library/PrivateFrameworks/TrustEvaluationAgent.framework/Versions/A/Resources';shutil.copytree(resource,version/'Resources');assert plistlib.loads((resource/'Info.plist').read_bytes())['CFBundleExecutable']==name
   for path,value in [(framework/'Versions/Current','A'),(framework/name,'Versions/Current/'+name),(framework/'Resources','Versions/Current/Resources')]:path.symlink_to(value)
  else:destination=pending/'libraries'/name
  shutil.copy2(root/source,destination);images.append(dict(target=target,original=original,original_sha256=digest(original),source=source,source_sha256=digest(source),reconstruction=report_name,reconstruction_sha256=digest(report_name),selected=str((base/destination.relative_to(pending)).relative_to(root)),exports=report['exports']))
 for name in ['libraries','frameworks']:
  destination=base/name;previous=base/(name+'.previous')
  if previous.exists():shutil.rmtree(previous)
  if destination.exists():destination.replace(previous)
  (pending/name).replace(destination)
  if previous.exists():shutil.rmtree(previous)
 pending.rmdir()
 files={str(p.relative_to(root)):digest(str(p.relative_to(root))) for name in ['libraries','frameworks'] for p in (base/name).rglob('*') if p.is_file()};links={str(p.relative_to(root)):os.readlink(p) for p in (base/'frameworks').rglob('*') if p.is_symlink()}
 record=dict(images=images,files=files,symlinks=links,libraries=str((base/'libraries').relative_to(root)),frameworks=str((base/'frameworks').relative_to(root)),installed=False,runtime_execution_verified=False,trust_evaluation_protocol_verified=False,cryptex_mounting_verified=False,full_xcode_build_ready=False)
 (root/'artifacts/cryptex-native-stage.json').write_text(json.dumps(record,indent=2)+'\n');print('Staged',len(images),'original images; no emulated approval, mounting or trust success')
