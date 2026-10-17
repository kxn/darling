#!/usr/bin/env python3
"""Execute source CoreCrypto under Darling; compare with Python's OpenSSL HMAC."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,hmac,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument("--native",action="store_true");args=parser.parse_args()
m=runpy.run_path(str(root/('scripts/commoncrypto-original-profile.py' if args.native else 'scripts/corecrypto-hkdf-profile.py')));p=m['profile']();env=m['environment'](p)
build=root/'runtime/corecrypto-hkdf-source';sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
source='fixtures/hello/corecrypto-hkdf.c';binary=build/'test';obj=build/'test.o'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-DPLATFORM_MacOSX=1','-isysroot',str(sdk),'-I',str(root/'vendor/darling/src/external/corecrypto/include'),'-O2','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-L'+str(build/'libraries'),'-lcorecrypto','-lSystem',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+(['CORECRYPTO_EXPECTED_OWNER=/runtime/rebuilt-corecrypto-original-native-v2/','CORECRYPTO_VALID_POINTERS_ONLY=1'] if args.native else [])+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))]
r=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True);log='logs/corecrypto-hkdf-'+('native-' if args.native else '')+'test.log';(root/log).write_text(r.stdout+r.stderr)
key=bytes((i*17+3)&255 for i in range(1024));salt=bytes((i*23+7)&255 for i in range(1024));info=bytes((i*31+11)&255 for i in range(1024));message=bytes((i*47+13)&255 for i in range(1024))
checks=0
for line in r.stdout.splitlines():
    if line.startswith('HMAC '):
        _,name,kl,ml,got=line.split();expected=hmac.new(key[:int(kl)],message[:int(ml)],name).hexdigest()
    elif line.startswith('HKDF '):
        parts=line.split();_,name,il,sl,cl,ol=parts[:6];got=parts[6] if len(parts)==7 else '';n=int(ol)
        prk=hmac.new(salt[:int(sl)],key[:int(il)],name).digest();previous=b'';output=b''
        for i in range(1,(n+len(prk)-1)//len(prk)+1):
            previous=hmac.new(prk,previous+info[:int(cl)]+bytes([i]),name).digest();output+=previous
        expected=output[:n].hex()
    else:continue
    assert got==expected,line[:150];checks+=1
verified=r.returncode==0 and checks==210 and 'CORECRYPTO_HKDF_BOUNDARIES_OK' in r.stdout
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),source_runtime=p['source_runtime'],corecrypto=p['native_original_corecrypto'] if args.native else p['source_corecrypto_hkdf'],command=command,exit_status=r.returncode,log=log,log_sha256=digest(log),source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),independent_HMAC_HKDF_cases=checks,algorithms=['SHA1','SHA224','SHA256','SHA384','SHA512'],runtime_execution_verified=verified,invalid_null_pointer_preconditions_exercised=not args.native,full_CoreCrypto_implemented=False)
(root/('artifacts/corecrypto-hkdf-'+('native-' if args.native else '')+'test.json')).write_text(json.dumps(record,indent=2)+'\n')
print('CoreCrypto independent comparisons:',checks,'exit:',r.returncode,'verified:',verified)
if not verified:print((r.stdout+r.stderr)[-3000:])
raise SystemExit(0 if verified else 1)
