#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent;m=runpy.run_path(str(root/'scripts/commoncrypto-original-profile.py'));p=m['profile']()
build=root/'runtime/native-crypto-constants';build.mkdir(exist_ok=True);references=['artifacts/security-cryptokit-constants-native-reference.json','artifacts/crypto-token-parameters-native-reference.json','artifacts/local-authentication-error-native-reference.json'];values={}
for name in references:
    d=json.loads((root/name).read_text());values.update(d['values'] if 'values' in d else {d['symbol']:d['value']})
header=build/'native-crypto-constants.inc';header.write_text('static const struct { const char *name, *value; } constants[] = {\n'+''.join('{'+json.dumps(k)+','+json.dumps(v)+'},\n' for k,v in values.items())+'};\n')
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';source='fixtures/hello/native-crypto-constants.c';obj=build/'test.o';binary=build/'test'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-I',str(build),'-O2','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-lSystem','-framework','CoreFoundation',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))];r=subprocess.run(command,cwd=root,env=m['environment'](p),capture_output=True,text=True);text=r.stdout+r.stderr;log='logs/native-crypto-constants-test.log';(root/log).write_text(text);verified=r.returncode==0 and 'NATIVE_CRYPTO_CONSTANT_TYPES_VALUES_COPY_OK checks=17' in text
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest();record=dict(checked_at=datetime.now(timezone.utc).isoformat(),command=command,exit_status=r.returncode,log=log,log_sha256=digest(log),runtime_execution_verified=verified,constants=values,references={n:digest(n) for n in references},source=source,source_sha256=digest(source),header=str(header.relative_to(root)),header_sha256=digest(header),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),hardware_services_verified=False)
(root/'artifacts/native-crypto-constants-test.json').write_text(json.dumps(record,indent=2)+'\n');print(r.returncode,text);raise SystemExit(0 if verified else 1)
