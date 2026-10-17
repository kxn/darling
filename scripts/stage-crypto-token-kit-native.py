#!/usr/bin/env python3
from pathlib import Path
import fcntl,hashlib,json,shutil
root=Path(__file__).resolve().parent.parent;digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
target='crypto-token-kit-native-original';report='runtime/rebuilt-'+target+'/reconstruction.json';d=json.loads((root/report).read_text());original='runtime/fullsystem-libraries/System/Library/Frameworks/CryptoTokenKit.framework/Versions/A/CryptoTokenKit';source='runtime/rebuilt-'+target+'/CryptoTokenKit'
assert digest(original)==d['original_image_sha256'] and digest(source)==d['staged_image_sha256'];assert not d['backend_call_overrides'] and not d['redirected_imports']
base=root/'runtime/crypto-token-kit-native';framework=base/'frameworks/CryptoTokenKit.framework';output=framework/'Versions/A/CryptoTokenKit'
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);output.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/source,output)
    for path,destination in [(framework/'Versions/Current','A'),(framework/'CryptoTokenKit','Versions/Current/CryptoTokenKit')]:
        if not path.is_symlink():path.symlink_to(destination)
record=dict(original=original,original_sha256=digest(original),source=source,source_sha256=digest(source),reconstruction=report,reconstruction_sha256=digest(report),framework=str(output.relative_to(root)),framework_sha256=digest(output),exports=d['exports'],installed=False,hardware_token_service_verified=False,runtime_execution_verified=False)
(root/'artifacts/crypto-token-kit-native-stage.json').write_text(json.dumps(record,indent=2)+'\n');print('Staged complete original CryptoTokenKit',d['exports'],'exports')
