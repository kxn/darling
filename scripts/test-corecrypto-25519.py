#!/usr/bin/env python3
"""Compare the Darwin CoreCrypto ABI against independent Linux cryptography."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,subprocess
import cryptography
from cryptography.hazmat.primitives.asymmetric import x25519,ed25519
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument("--native",action="store_true");args=parser.parse_args()
m=runpy.run_path(str(root/('scripts/commoncrypto-original-profile.py' if args.native else 'scripts/corecrypto-hkdf-profile.py')));p=m['profile']();env=m['environment'](p)
build=root/'runtime/corecrypto-hkdf-source';sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
source='fixtures/hello/corecrypto-25519.c';binary=build/'25519-test';obj=build/'25519-test.o'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-DPLATFORM_MacOSX=1','-isysroot',str(sdk),'-I',str(root/'vendor/darling/src/external/corecrypto/include'),'-O2','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-L'+str(build/'libraries'),'-lcorecrypto','-lSystem',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+(['CORECRYPTO_EXPECTED_OWNER=/runtime/rebuilt-corecrypto-original-native-v2/','CORECRYPTO_VALID_POINTERS_ONLY=1'] if args.native else [])+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))]
r=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True);log='logs/corecrypto-25519-'+('native-' if args.native else '')+'test.log';(root/log).write_text(r.stdout+r.stderr)
raw=lambda key:key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)
checks=0
for line in r.stdout.splitlines():
    fields=line.split()
    if line.startswith('X25519 '):
        _,k,pk,peerpk,shared=fields;k=int(k)
        sk=x25519.X25519PrivateKey.from_private_bytes(bytes((k*13+i*7+11)&255 for i in range(32)))
        peer=x25519.X25519PrivateKey.from_private_bytes(bytes((k*19+i*11+5)&255 for i in range(32)))
        assert raw(sk).hex()==pk and raw(peer).hex()==peerpk and sk.exchange(peer.public_key()).hex()==shared,line
    elif line.startswith('ED25519 '):
        _,k,n,pk,sig=fields;k=int(k);n=int(n)
        sk=ed25519.Ed25519PrivateKey.from_private_bytes(bytes((k*29+i*17+9)&255 for i in range(32)))
        msg=bytes((i*23+7)&255 for i in range(n));assert raw(sk).hex()==pk,line
        if not args.native:assert sk.sign(msg).hex()==sig,line
        sk.public_key().verify(bytes.fromhex(sig),msg)
    elif line.startswith('ED25519_GENERATED '):
        sk=ed25519.Ed25519PrivateKey.from_private_bytes(bytes((i*17+3)&255 for i in range(32)));assert raw(sk).hex()==fields[1]
    else:continue
    checks+=1
verified=r.returncode==0 and checks==113 and 'CORECRYPTO_25519_KEYS_SIGNATURE_TAMPER_ZERO_PEER_RNG_ERRORS_OK' in r.stdout
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),source_runtime=p['source_runtime'],corecrypto=p['native_original_corecrypto'] if args.native else p['source_corecrypto_hkdf'],command=command,exit_status=r.returncode,log=log,log_sha256=digest(log),source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),independent_cryptography_cases=checks,cryptography_version=cryptography.__version__,runtime_execution_verified=verified,invalid_null_pointer_preconditions_exercised=not args.native,source_backend_randomized_coordinate_blinding_implemented=False,error_output_zeroing_verified=not args.native,signature_byte_identity_required=not args.native,custom_Ed25519_digest_exercised=False)
(root/('artifacts/corecrypto-25519-'+('native-' if args.native else '')+'test.json')).write_text(json.dumps(record,indent=2)+'\n');print('CoreCrypto 25519 comparisons:',checks,'exit:',r.returncode,'verified:',verified)
if not verified:print((r.stdout+r.stderr)[-3000:])
raise SystemExit(0 if verified else 1)
