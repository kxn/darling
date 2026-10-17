#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
python3 - <<'PY'
from pathlib import Path
import struct
destination=Path('runtime/macho-slices-source/fixtures');destination.mkdir(exist_ok=True)
arches=[(0x1000007,3),(0x100000c,0)]
headers=[struct.pack('<8I',0xfeedfacf,cpu,subtype,1,0,0,0,0) for cpu,subtype in arches]
for is64 in [False,True]:
    data=bytearray(0x2020);data[:8]=struct.pack('>II',0xcafebabf if is64 else 0xcafebabe,2)
    for i,((cpu,subtype),header) in enumerate(zip(arches,headers)):
        entry=struct.pack('>IIQQII',cpu,subtype,(i+1)*0x1000,len(header),12,0) if is64 else struct.pack('>IIIII',cpu,subtype,(i+1)*0x1000,len(header),12)
        data[8+i*len(entry):8+(i+1)*len(entry)]=entry
        data[(i+1)*0x1000:(i+1)*0x1000+len(header)]=header
    (destination/('fat64' if is64 else 'fat32')).write_bytes(data)
(destination/'thin64').write_bytes(headers[0]);(destination/'thin32').write_bytes(struct.pack('<7I',0xfeedface,7,3,1,0,0,0))
(destination/'random').write_bytes(b'x'*128)
hidden=bytearray((destination/'fat32').read_bytes());struct.pack_into('>I',hidden,4,1)
(destination/'hidden32').write_bytes(hidden)
maximum=bytearray(0x11020);maximum[:8]=struct.pack('>II',0xcafebabe,16)
for i in range(17):
    cpu,subtype=(0x1000007,i) if i<16 else (0x100000c,0)
    header=struct.pack('<8I',0xfeedfacf,cpu,subtype,1,0,0,0,0)
    maximum[8+i*20:28+i*20]=struct.pack('>IIIII',cpu,subtype,(i+1)*0x1000,32,12)
    maximum[(i+1)*0x1000:(i+1)*0x1000+32]=header
(destination/'maximum-hidden32').write_bytes(maximum)
base=bytearray((destination/'fat32').read_bytes());cases={}
x=bytearray(base);struct.pack_into('>I',x,4,17);cases['too-many']=x
x=bytearray(base);struct.pack_into('>I',x,16,0xfffff000);cases['bounds']=x
x=bytearray(base);x[28:48]=x[8:28];cases['duplicate']=x
x=bytearray(base);struct.pack_into('>I',x,36,0x1010);cases['overlap']=x
x=bytearray(base);struct.pack_into('<I',x,0x1004,0x100000c);cases['wrong-cpu']=x
x=bytearray(base);struct.pack_into('>I',x,16,0x1001);x[0x1001:0x1021]=headers[0];struct.pack_into('<I',x,0x100d,2);cases['unaligned']=x
for name,data in cases.items():(destination/name).write_bytes(data)
PY
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos15.4 -isysroot "$sdk" -fblocks \
    -c fixtures/hello/macho-slices.c -o runtime/macho-slices-source/test.o
ld64.lld-19 -arch x86_64 -platform_version macos 15.4 15.4 -syslibroot "$guest" \
    -L runtime/native-library-stage -lDarlingCacheIntrospection -lSystem \
    runtime/macho-slices-source/test.o -o artifacts/macho-slices
workspace=/Volumes/SystemRoot/workspace
timeout -k 5 45 bin/darling shell /usr/bin/env \
    DYLD_LIBRARY_PATH="$workspace/runtime/native-library-stage:$workspace/runtime/rebuilt-der:/usr/lib/swift" \
    "$workspace/artifacts/macho-slices" "$workspace/runtime/macho-slices-source/fixtures" \
    /Applications/Xcode.app/Contents/SharedFrameworks/DVTInstrumentsFoundation.framework/Versions/A/DVTInstrumentsFoundation \
    > logs/macho-slices.log 2>&1
rg -q '^APPLE_MACHO_SLICE_UTILITIES_THIN_FAT32_FAT64_STOP_FD_ERRORS_384_BAD_FILES_NO_MAPPING_LEAK_AND_ACTUAL_XCODE_OK ' logs/macho-slices.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
root=Path.cwd();p=root/'artifacts/macho-slices-source.json';report=json.loads(p.read_text())
digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
for name,value in report['generated_files'].items():assert digest(root/'runtime/macho-slices-source'/name)==value
report.update(checked_at=datetime.now(timezone.utc).isoformat(),runtime_execution_verified=True,
    library_sha256=digest(root/'runtime/native-library-stage/libDarlingCacheIntrospection.dylib'),
    tests=['Thin 32/64-bit headers and actual Xcode universal file', 'Big-endian fat32/fat64 headers, offsets, sizes, callback order and early stop',
        'Legacy hidden ARM64 descriptor, including 16 declared plus one hidden slice; early stop does not invoke hidden callback',
        'FD offset remains unchanged; null callback; ENOENT/EACCES/EFTYPE/EBADF',
        '384 malformed-fat rejections with zero callbacks and no retained fixture mappings'],
    full_macho_validation_claimed=False,arm_execution=False,log='logs/macho-slices.log')
p.write_text(json.dumps(report,indent=2)+'\n')
PY
