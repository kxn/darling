#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
python3 - <<'PY'
from pathlib import Path
import runpy,json,hashlib,struct
root=Path.cwd();r=json.loads(Path('config/constant-float-abi.json').read_text())
source=root/'runtime/fullsystem-libraries'/r['provider'].lstrip('/')
assert hashlib.sha256(source.read_bytes()).hexdigest()==r['provider_sha256']
ns=runpy.run_path('scripts/dsc-image.py',init_globals={
    'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
cls=ns['resolve'](r['provider'],'_OBJC_CLASS_$_'+r['class'])
assert ns['pointer'](cls+8)==ns['resolve'](r['provider'],'_OBJC_CLASS_$_NSNumber')
ro=ns['pointer'](cls+32)&~7
_,start,size,_=struct.unpack('<4I',ns['read'](ro,16))
assert (start,size)==(r['instance_start'],r['instance_size'])
lst=ns['pointer'](ro+48);assert struct.unpack('<II',ns['read'](lst,8))==(32,1)
entry=lst+8
assert ns['read'](ns['pointer'](entry+8),len(r['ivar_name'])+1)==r['ivar_name'].encode()+b'\0'
assert ns['read'](ns['pointer'](entry+16),2)==r['ivar_type'].encode()+b'\0'
assert struct.unpack('<I',ns['read'](ns['pointer'](entry),4))[0]==r['ivar_offset']
assert struct.unpack('<II',ns['read'](entry+24,8))==(r['ivar_alignment_log2'],r['ivar_size'])
PY
mkdir -p runtime/constant-float-number
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -O2 -c scripts/constant-float-number.m \
    -o runtime/constant-float-number/float.o
ld64.lld-19 -dylib -arch x86_64 -platform_version macos 11 11 \
    -syslibroot "$guest" -L "$guest/usr/lib" -lSystem -lobjc -framework Foundation \
    -install_name /usr/lib/libDarlingConstantFloat.dylib \
    runtime/constant-float-number/float.o -o runtime/native-library-stage/libDarlingConstantFloat.dylib.pending
mv runtime/native-library-stage/libDarlingConstantFloat.dylib.pending runtime/native-library-stage/libDarlingConstantFloat.dylib
