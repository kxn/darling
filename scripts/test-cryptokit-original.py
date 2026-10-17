#!/usr/bin/env python3
"""Execute original SDK CryptoKit APIs; independently check every crypto result."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,hmac,json,runpy,subprocess
from cryptography.hazmat.primitives.asymmetric import ec,ed25519,x25519
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
from cryptography.hazmat.primitives.ciphers.aead import AESGCM,ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
parser=argparse.ArgumentParser();parser.add_argument("--debug",action="store_true");args=parser.parse_args()
root=Path(__file__).resolve().parent.parent;m=runpy.run_path(str(root/'scripts/commoncrypto-original-profile.py'));p=m['profile']();env=m['environment'](p);guest='/Volumes/SystemRoot/workspace/'
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';sg='/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';tc='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain';digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-O2','-c','fixtures/hello/cryptokit-original-owner.c','-o','artifacts/cryptokit-original-owner.o'],cwd=root,check=True)
steps=[('compile',[tc+'/usr/bin/swift-frontend','-c',guest+'fixtures/hello/cryptokit-original.swift','-target','x86_64-apple-macos26.0','-sdk',sg,'-module-name','OriginalCryptoKitSDKProbe','-o',guest+'artifacts/cryptokit-original.o']),('link',[tc+'/usr/bin/clang','-target','x86_64-apple-macos26.0','-isysroot',sg,guest+'artifacts/cryptokit-original.o',guest+'artifacts/cryptokit-original-owner.o','-L/usr/lib/swift','-lswiftCore','-lswiftSwiftOnoneSupport','-framework','Foundation','-framework','CryptoKit','-Wl,-rpath,/usr/lib/swift','-o',guest+'artifacts/cryptokit-original']),('execute',[guest+'artifacts/cryptokit-original']+(['--debug'] if args.debug else []))]
checks=[];output=''
for name,tail in steps:
    command=p['command'][:-2]+tail
    if name=='compile':command[3]='180'
    r=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True);output=r.stdout+r.stderr;log='logs/cryptokit-original-'+name+'.log';(root/log).write_text(output);checks.append(dict(step=name,command=command,exit_status=r.returncode,log=log,log_sha256=digest(log)));print(name,r.returncode,output[-2500:],flush=True)
    if r.returncode:break
message=b'Original CryptoKit on Linux Darling';aad=b'authenticated metadata';key=bytes(range(32));nonce=bytes(range(12));independent=0
if len(checks)==3 and checks[-1]['exit_status']==0:
    for line in output.splitlines():
        fields=line.split();kind=fields[0] if fields else ''
        if kind=='P256':
            pub=ec.derive_private_key(1,ec.SECP256R1()).public_key();assert pub.public_bytes(Encoding.X962,PublicFormat.UncompressedPoint).hex()==fields[1];pub.verify(bytes.fromhex(fields[2]),message,ec.ECDSA(hashes.SHA256()))
        elif kind=='X25519':
            priv=x25519.X25519PrivateKey.from_private_bytes(key);peer=x25519.X25519PrivateKey.from_private_bytes(bytes([7])*32);assert priv.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw).hex()==fields[1] and priv.exchange(peer.public_key()).hex()==fields[2]
        elif kind=='ED25519':
            priv=ed25519.Ed25519PrivateKey.from_private_bytes(key);assert priv.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw).hex()==fields[1];priv.public_key().verify(bytes.fromhex(fields[2]),message)
        elif kind in ['AESGCM','CHACHA']:
            cipher=AESGCM(key) if kind=='AESGCM' else ChaCha20Poly1305(key);assert cipher.encrypt(nonce,message,aad).hex()==fields[1]+fields[2]
        elif kind in ['SHA256','SHA3_256','SHA3_384','SHA3_512']:assert hashlib.new(kind.lower(),message).hexdigest()==fields[1]
        elif kind=='HMAC':assert hmac.new(key,message,'sha256').hexdigest()==fields[1]
        elif kind=='HKDF':assert HKDF(algorithm=hashes.SHA256(),length=42,salt=b'salt',info=b'info').derive(key).hex()==fields[1]
        else:continue
        independent+=1
verified=len(checks)==3 and checks[-1]['exit_status']==0 and independent==11 and 'ORIGINAL_CRYPTOKIT_SOFTWARE_CHECKS_OK' in output
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),source_runtime=p['source_runtime'],corecrypto=p['native_original_corecrypto'],cryptokit=p['native_original_cryptokit'],crypto_token_kit=p['native_crypto_token_kit'],checks=checks,independent_crypto_results=independent,original_Apple_SDK_interface_used=True,runtime_execution_verified=verified,SecureEnclave_verified=False,full_CryptoKit_compatibility=False,sources={n:digest(n) for n in ['fixtures/hello/cryptokit-original.swift','fixtures/hello/cryptokit-original-owner.c']})
(root/'artifacts/cryptokit-original-test.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if verified else 1)
