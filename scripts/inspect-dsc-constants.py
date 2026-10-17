#!/usr/bin/env python3
"""Read ASCII CFString constant values from the reference x86_64 dyld cache.

Analysis only: this does not reconstruct or install executable cache images.
Usage: inspect-dsc-constants.py extracted-image symbol [symbol ...]
"""
import json
from pathlib import Path
import struct
import subprocess
import sys

project=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(project/'vendor/DyldExtractor/src'))
from DyldExtractor.dyld.dyld_context import DyldContext
from DyldExtractor.dyld.dyld_structs import dyld_cache_mapping_and_slide_info, dyld_cache_slide_info2

cache=Path(globals().get('REFERENCE_CACHE_PATH',
    project/'runtime/recovery/macOS Base System/System/Library/dyld/dyld_shared_cache_x86_64'))
library_root=Path(globals().get('REFERENCE_LIBRARY_ROOT',project/'runtime/recovery-libraries'))
subcaches=sorted(path for path in cache.parent.glob(cache.name+'.[0-9][0-9]') if path.is_file())
contexts=[DyldContext(path.open('rb')) for path in [cache,*subcaches]]
mappings=[]
for ctx in contexts:
    for i in range(ctx.header.mappingWithSlideCount):
        mapping=dyld_cache_mapping_and_slide_info(ctx.file,ctx.header.mappingWithSlideOffset+i*56)
        version=struct.unpack_from('<I',ctx.file,mapping.slideInfoFileOffset)[0] if mapping.slideInfoFileSize else 0
        if version not in (0,2):raise SystemExit(f'Unsupported cache slide version {version}')
        info=dyld_cache_slide_info2(ctx.file,mapping.slideInfoFileOffset) if version==2 else None
        mappings.append((ctx,mapping,info))

def locate(address):
    for ctx,mapping,info in mappings:
        if mapping.address<=address<mapping.address+mapping.size:
            return ctx,mapping,info,mapping.fileOffset+address-mapping.address
    raise ValueError(f'Address outside cache mappings: {address:#x}')

def read(address,size):
    ctx,mapping,_,offset=locate(address)
    if address+size>mapping.address+mapping.size:raise ValueError('Read crosses mapping boundary')
    return bytes(ctx.file[offset:offset+size])

def pointer(address):
    raw=struct.unpack('<Q',read(address,8))[0]
    _,_,info,_=locate(address)
    if info:
        raw &= (~info.delta_mask)&((1<<64)-1)
        if raw:raw+=info.value_add
    return raw

def main():
    if len(sys.argv)<3:raise SystemExit(__doc__)
    symbols={parts[-1]:int(parts[0],16) for line in subprocess.check_output(
        ['llvm-nm-19','--defined-only','--extern-only',sys.argv[1]],text=True).splitlines()
        if len(parts:=line.split())==3}
    report={}
    for symbol in sys.argv[2:]:
        obj=pointer(symbols[symbol])
        chars=pointer(obj+16)
        length=struct.unpack('<Q',read(obj+24,8))[0]
        if length>4096:raise ValueError('Unexpected CFString length')
        flags=struct.unpack('<I',read(obj+8,4))[0]
        if (flags & 0xff)!=0xc8:raise ValueError(f'Not an ASCII CFString: flags={flags:#x}')
        report[symbol]={'value':read(chars,length).decode('ascii'),
                        'global_address':hex(symbols[symbol]),'cfstring_flags':hex(flags)}
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
