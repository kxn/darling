#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,hmac,json,struct,runpy,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/crypto-quarantine-runtime-profile.py'));p=m['profile'](False)
build=root/'runtime/coreutils-crypto-source';sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
def pattern(n,seed):return bytes((i*37+seed)&255 for i in range(n))
def hkdf(alg,key,salt,info,n):
    prk=hmac.digest(salt or bytes(hashlib.new(alg).digest_size),key,alg);previous=b'';result=b''
    for counter in range(1,256):
        if len(result)>=n:break
        previous=hmac.digest(prk,previous+info+bytes([counter]),alg);result+=previous
    assert len(result)>=n;return result[:n]
rows=[];payload=bytearray()
for ai,alg in enumerate(['sha1','sha256','sha512']):
    size=hashlib.new(alg).digest_size
    for n in [0,1,3,55,56,63,64,65,111,112,127,128,129,255,1024,4096]:
        data=pattern(n,11);rows.append((0,ai,b'',b'',b'',data,hashlib.new(alg,data).digest()))
        for kn in [0,1,20,63,64,65,127,128,129,257]:
            key=pattern(kn,79);rows.append((1,ai,key,b'',b'',data,hmac.digest(key,data,alg)))
    for kn in [0,22,131]:
        for sn in [0,13,141]:
            for infon in [0,73]:
                key=pattern(kn,17);salt=pattern(sn,93);info=pattern(infon,29)
                for n in [0,1,size-1,size,size+7,255*size]:rows.append((2,ai,key,salt,info,b'',hkdf(alg,key,salt,info,n)))
for kind,ai,key,salt,info,data,out in rows:payload+=struct.pack('<7I',kind,ai,len(key),len(salt),len(info),len(data),len(out))+key+salt+info+data+out
vectors=build/'independent-vectors.bin';vectors.write_bytes(payload)
source='fixtures/hello/coreutils-crypto-source.c';obj=build/'test.o';binary=build/'test'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-I'+str(root/'vendor/darling/src/private-frameworks/CoreUtils/include'),'-Wno-deprecated-declarations','-O2','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-L'+str(sdk/'usr/lib/system'),'-F'+str(build/'frameworks'),'-framework','CoreUtils','-lcommonCrypto','-lSystem',str(obj),'-o',str(binary)],check=True)
guest=lambda n:'/Volumes/SystemRoot/workspace/'+str(n.relative_to(root))
command=p['command'][:-2]+[guest(binary),guest(vectors)];log='logs/coreutils-crypto-source-test.log'
with (root/log).open('w') as stream:r=subprocess.run(command,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
text=(root/log).read_text();print(text[-4000:],flush=True);digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
success=r.returncode==0 and 'COREUTILS_SOURCE_DESCRIPTOR_ABI_HASH_HMAC_HKDF_INDEPENDENT_VECTORS_AND_GUARDS_OK' in text
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'source':source,'source_sha256':digest(source),'binary':str(binary.relative_to(root)),'binary_sha256':digest(str(binary.relative_to(root))),'vectors':str(vectors.relative_to(root)),'vectors_sha256':digest(str(vectors.relative_to(root))),'independent_reference':'Python hashlib/hmac, separate Linux OpenSSL implementation; HKDF extract/expand computed by this driver','cases':len(rows),'hash_cases':sum(x[0]==0 for x in rows),'HMAC_cases':sum(x[0]==1 for x in rows),'HKDF_cases':sum(x[0]==2 for x in rows),'log':log,'log_sha256':digest(log),'exit_status':r.returncode,'independent_crypto_vectors_verified':success,'full_xcode_build_ready':False}
(root/'artifacts/coreutils-crypto-source-test.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if success else 1)
