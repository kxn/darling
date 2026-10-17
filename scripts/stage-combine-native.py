#!/usr/bin/env python3
"""Stage complete original Intel Combine; runtime compatibility is tested separately."""
from pathlib import Path
from datetime import datetime,timezone
import fcntl,hashlib,json,shutil
root=Path(__file__).resolve().parent.parent;digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
pin=json.loads((root/'config/cache-image-pins.json').read_text())['combine-native'];original='runtime/fullsystem-libraries'+pin['path'];source='runtime/rebuilt-combine-native/Combine';reconstruction='runtime/rebuilt-combine-native/reconstruction.json';r=json.loads((root/reconstruction).read_text());assert digest(original)==pin['sha256']==r['original_image_sha256'];assert digest(source)==r['staged_image_sha256']
assert r['experimental_swift_unverified'] and r['swift_metadata'] and len(r['objc_metadata']['classes'])==4
assert not r['redirected_imports'] and not r['backend_call_overrides']
library='runtime/combine-native/frameworks/Combine.framework/Versions/A/Combine';target=root/library;target.parent.mkdir(parents=True,exist_ok=True)
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);temp=target.with_suffix('.pending');shutil.copyfile(root/source,temp);temp.replace(target)
f=target.parent.parent.parent
for p,v in [(f/'Versions/Current','A'),(f/'Combine','Versions/Current/Combine')]:
 if not p.is_symlink():p.symlink_to(v)
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),original=original,original_sha256=digest(original),source=source,source_sha256=digest(source),library=library,library_sha256=digest(library),reconstruction=reconstruction,reconstruction_sha256=digest(reconstruction),exports=r['exports'],objc_classes=r['objc_metadata']['classes'],swift_metadata=r['swift_metadata'],installed=False,runtime_execution_verified=False,scope='Full original Intel Combine code and original Swift metadata, with cache relocations restored. No backend-call override, imported-function redirect or replacement publisher object. Runtime behavior and general ABI compatibility are not inferred from structural recovery.')
(root/'artifacts/combine-native-stage.json').write_text(json.dumps(record,indent=2)+'\n');print('Staged full original Combine,',r['exports'],'exports')
