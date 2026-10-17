#!/usr/bin/env python3
"""Compare original Intel crypto to Linux OpenSSL 3 and a separate GF(2^128) reference."""
from pathlib import Path
from datetime import datetime,timezone
import ctypes,ctypes.util,hashlib,json,re,runpy,struct,subprocess
root=Path(__file__).resolve().parent.parent
features=set(next(line.split(':',1)[1].split() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('flags')));required_features=['ssse3','pclmulqdq'];assert set(required_features)<=features,'Direct internal assembly tests require actual CPU SSSE3/PCLMUL support'
m=runpy.run_path(str(root/'scripts/cryptex-native-profile.py'));p=m['profile'](False)
build=root/'runtime/crypto42-native-test';build.mkdir(exist_ok=True);lib=ctypes.CDLL(ctypes.util.find_library('crypto'));vp=ctypes.c_void_p
for name in ['AES_set_encrypt_key','Camellia_set_key']:
 f=getattr(lib,name);f.argtypes=[vp,ctypes.c_int,vp];f.restype=ctypes.c_int
for name in ['AES_encrypt','Camellia_encrypt']:
 f=getattr(lib,name);f.argtypes=[vp,vp,vp];f.restype=None
for name in ['AES_cbc_encrypt','Camellia_cbc_encrypt']:
 f=getattr(lib,name);f.argtypes=[vp,vp,ctypes.c_size_t,vp,vp,ctypes.c_int];f.restype=None
lib.WHIRLPOOL.argtypes=[vp,ctypes.c_size_t,vp];lib.WHIRLPOOL.restype=vp
pattern=lambda n,seed:bytes((i*37+seed)&255 for i in range(n))
rows=[]
for kind,alg in enumerate(['sha1','sha256','sha512','whirlpool']):
 for n in [0,1,3,55,56,63,64,65,111,112,127,128,129,255,1024,4096]:
  data=pattern(n,19)
  if alg=='whirlpool':
   output=ctypes.create_string_buffer(64);assert lib.WHIRLPOOL(data,n,output);expected=output.raw
  else:expected=hashlib.new(alg,data).digest()
  rows.append((kind,b'',bytes(16),data,expected))
for kind,prefix in [(4,'AES'),(5,'Camellia')]:
 for kn in [16,24,32]:
  for n in [16,32,128,256,1024,4096]:
   for seed in [0,7,191]:
    key=pattern(kn,seed);iv=pattern(16,seed+1);data=pattern(n,seed+3);context=ctypes.create_string_buffer(1024);out=ctypes.create_string_buffer(n);ecb=ctypes.create_string_buffer(16);current=ctypes.create_string_buffer(iv,16)
    assert getattr(lib,'AES_set_encrypt_key' if kind==4 else 'Camellia_set_key')(key,kn*8,context)==0
    getattr(lib,prefix+'_cbc_encrypt')(data,out,n,context,current,1);getattr(lib,prefix+'_encrypt')(data,ecb,context)
    rows.append((kind,key,iv,data,out.raw+ecb.raw))
def multiply(x,y):
 z=0;v=y
 for bit in range(127,-1,-1):
  if (x>>bit)&1:z^=v
  v=(v>>1)^(0xe1000000000000000000000000000000 if v&1 else 0)
 return z
for n in [16,32,64,128,256,1024]:
 for seed in [0,1,19,237]:
  h=pattern(16,seed);iv=pattern(16,seed+9);data=pattern(n,seed+11);H=int.from_bytes(h,'big');Xi=int.from_bytes(iv,'big');single=multiply(Xi,H);current=Xi
  for i in range(0,n,16):current=multiply(current^int.from_bytes(data[i:i+16],'big'),H)
  table=b''.join(struct.pack('<QQ',v>>64,v&((1<<64)-1)) for nibble in range(16) for v in [multiply(nibble<<124,H)])
  rows.append((6,h+table,iv,data,single.to_bytes(16,'big')+current.to_bytes(16,'big')))
payload=struct.pack('<I',len(rows))
for kind,key,iv,data,expected in rows:payload+=struct.pack('<4I',kind,len(key),len(data),len(expected))+key+iv+data+expected
vectors=build/'independent-vectors.bin';vectors.write_bytes(payload)
ns=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h','REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'});obj=ns['image']('/usr/lib/libcrypto.42.dylib');base=next(s[1] for s in obj.segments if s[0]=='__TEXT')
names=['vpaes_set_encrypt_key','vpaes_set_decrypt_key','vpaes_encrypt','vpaes_decrypt','vpaes_cbc_encrypt','bsaes_cbc_encrypt','gcm_gmult_4bit','gcm_ghash_4bit','gcm_init_clmul','gcm_gmult_clmul','gcm_ghash_clmul'];symbols={}
for line in subprocess.check_output(['llvm-nm-19','--numeric-sort',str(root/'runtime/fullsystem-libraries/usr/lib/libcrypto.42.dylib')],text=True).splitlines():
 match=re.match(r'^([0-9a-f]+)\s+\S\s+_(.*)$',line)
 if match and match[2] in names:symbols[match[2]]=int(match[1],16)-base
assert set(names)==set(symbols)
header=build/'native-addresses.h';header.write_text('\n'.join('#define OFFSET_'+name+' '+hex(value)+'ULL' for name,value in symbols.items())+'\n')
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';source='fixtures/hello/crypto42-native.c';obj=build/'test.o';binary=build/'test'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-I'+str(build),'-I'+str(root/'runtime/libressl-source-reference/libressl-2.6.5/include'),'-Wno-ignored-attributes','-Wno-unknown-attributes','-O2','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-lSystem',str(obj),'-o',str(binary)],check=True)
guest=lambda path:'/Volumes/SystemRoot/workspace/'+str(path.relative_to(root));command=p['command'][:-2]+[guest(binary),guest(vectors)];log='logs/crypto42-native-test.log'
with (root/log).open('w') as stream:r=subprocess.run(command,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
text=(root/log).read_text();print(text[-6000:],flush=True);digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest();success=r.returncode==0 and 'NATIVE_CRYPTO42_INDEPENDENT_DIGEST_AES_VPAES_BSAES_CAMELLIA_GHASH_4BIT_CLMUL_AND_GUARDS_OK' in text
headers={str(path.relative_to(root)):digest(str(path.relative_to(root))) for path in (root/'runtime/libressl-source-reference/libressl-2.6.5/include/openssl').glob('*.h')}
record=dict(actual_CPU_test_features={n:n in features for n in required_features},ABI_headers=headers,checked_at=datetime.now(timezone.utc).isoformat(),stage='artifacts/cryptex-native-stage.json',stage_sha256=digest('artifacts/cryptex-native-stage.json'),source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(str(binary.relative_to(root))),vectors=str(vectors.relative_to(root)),vectors_sha256=digest(str(vectors.relative_to(root))),native_addresses=str(header.relative_to(root)),native_addresses_sha256=digest(str(header.relative_to(root))),internal_offsets=symbols,reference='Linux '+lib._name+' OpenSSL 3 direct functions, Python hashlib, independent bit-serial GF(2^128) multiplication',cases=len(rows),counts={str(k):sum(row[0]==k for row in rows) for k in range(7)},command=command,exit_status=r.returncode,log=log,log_sha256=digest(log),native_algorithms_verified=success,whole_3447_export_API_verified=False,certificate_trust_verified=False)
(root/'artifacts/crypto42-native-test.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if success else 1)
