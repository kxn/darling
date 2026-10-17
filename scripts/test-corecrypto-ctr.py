#!/usr/bin/env python3
"""Compare Darling AES-CTR with OpenSSL ECB and independently formed counters."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument("--native",action="store_true");args=parser.parse_args()
m=runpy.run_path(str(root/('scripts/commoncrypto-original-profile.py' if args.native else 'scripts/corecrypto-hkdf-profile.py')));p=m['profile']();env=m['environment'](p)
build=root/'runtime/corecrypto-hkdf-source';sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
source='fixtures/hello/corecrypto-ctr.c';binary=build/'ctr-test';obj=build/'ctr-test.o'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-DPLATFORM_MacOSX=1','-isysroot',str(sdk),'-I',str(root/'vendor/darling/src/external/corecrypto/include'),'-O2','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-L'+str(build/'libraries'),'-lcorecrypto','-lSystem',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+(['CORECRYPTO_EXPECTED_OWNER=/runtime/rebuilt-corecrypto-original-native-v2/','CORECRYPTO_VALID_POINTERS_ONLY=1'] if args.native else [])+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))]
r=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True);log='logs/corecrypto-ctr-'+('native-' if args.native else '')+'test.log';(root/log).write_text(r.stdout+r.stderr)
checks=0
for line in r.stdout.splitlines():
    if not line.startswith('CTR '):continue
    fields=line.split();_,kl,v,n=fields[:4];kl=int(kl);v=int(v);n=int(n);got=fields[4] if len(fields)==5 else ''
    key=bytes((i*7+5)&255 for i in range(kl));iv=bytearray((i*11+3)&255 for i in range(16))
    if v:iv[8:]=bytes([255])*8
    if v==2:iv[15]=254
    counter=int.from_bytes(iv[8:],'big');blocks=b''.join(bytes(iv[:8])+((counter+i)%(1<<64)).to_bytes(8,'big') for i in range((n+15)//16))
    stream=subprocess.run(['openssl','enc','-aes-'+str(kl*8)+'-ecb','-K',key.hex(),'-nopad'],input=blocks,capture_output=True,check=True).stdout
    expected=bytes(a^((i*13+11)&255) for i,a in enumerate(stream[:n])).hex()
    assert got==expected,line[:120];checks+=1
verified=r.returncode==0 and checks==81 and 'CORECRYPTO_CTR_BOUNDARIES_OK' in r.stdout
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),source_runtime=p['source_runtime'],corecrypto=p['native_original_corecrypto'] if args.native else p['source_corecrypto_hkdf'],command=command,exit_status=r.returncode,log=log,log_sha256=digest(log),source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),independent_OpenSSL_cases=checks,runtime_execution_verified=verified,invalid_null_pointer_preconditions_exercised=not args.native,checks_cover=['AES128/192/256','one-shot/bytewise/split/in-place/decrypt','partial-keystream reset','64-bit counter carry and rollover','invalid key']+([] if args.native else ['null input']))
(root/('artifacts/corecrypto-ctr-'+('native-' if args.native else '')+'test.json')).write_text(json.dumps(record,indent=2)+'\n')
print('CoreCrypto CTR independent cases:',checks,'exit:',r.returncode,'verified:',verified)
if not verified:print((r.stdout+r.stderr)[-3000:])
raise SystemExit(0 if verified else 1)
