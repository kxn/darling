#!/usr/bin/env python3
"""Diagnose original Xcode chained import tables against selected runtime exports.

Read-only candidates: this does not traverse pointer chains or prove that every
import-table record is used, nor establish binding order, ABI or execution.
Negative global lookup ordinals and compressed symbol pools remain explicit gaps.
"""
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import argparse,json,runpy,struct

root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--inventory',type=Path,default=root/'artifacts/xcode-native-dependency-inventory.json')
parser.add_argument('--output',type=Path,default=root/'artifacts/xcode-chained-import-audit.json')
args=parser.parse_args()
Image=runpy.run_path(str(root/'scripts/audit-runtime-symbols.py'))['Image']
images=[Image(row) for row in json.loads(args.inventory.read_text())['images']]
aliases={}
for image in images:
    aliases[image.record['image']]=image
    for alias in image.record.get('aliases',[]):aliases[alias]=image
    if image.install_name:aliases[image.install_name]=image
def provider(name):
    if name in aliases:return aliases[name]
    found=[i for i in images if Path(i.record['image']).name==Path(name).name]
    return found[0] if len(found)==1 else None
def exported(image,name,seen=frozenset()):
    if image is None or (id(image),name) in seen:return False
    seen=seen|{(id(image),name)}
    if name in image.exports:
        entry=image.exports[name]
        if entry is None:return True
        ordinal,symbol=entry
        return 0<ordinal<=len(image.dependencies) and exported(provider(image.dependencies[ordinal-1]),symbol,seen)
    return any(exported(provider(image.dependencies[i-1]),name,seen) for i in image.reexports)
def slice_x86(data):
    if data[:4] in (bytes.fromhex('cafebabe'),bytes.fromhex('bebafeca'),bytes.fromhex('cafebabf')):
        endian='<' if data[:4]==bytes.fromhex('bebafeca') else '>'
        width=32 if data[:4]==bytes.fromhex('cafebabf') else 20
        for i in range(struct.unpack_from(endian+'I',data,4)[0]):
            at=8+i*width
            if struct.unpack_from(endian+'I',data,at)[0]==0x1000007:
                offset,length=struct.unpack_from(endian+('QQ' if width==32 else 'II'),data,at+8)
                return data[offset:offset+length]
        raise ValueError('No x86_64 slice')
    return data
missing={};gaps=[];special=Counter();checked=0;formats=Counter();audited=[]
for image in images:
    if not image.chained_fixups:continue
    try:
        data=slice_x86((root/image.record['host']).read_bytes());at=32;location=None
        for _ in range(struct.unpack_from('<I',data,16)[0]):
            command,length=struct.unpack_from('<II',data,at)
            if command==0x80000034:location=struct.unpack_from('<II',data,at+8)
            at+=length
        if location is None:raise ValueError('No chained-fixup command')
        offset,length=location
        if offset>len(data) or length>len(data)-offset or length<28:raise ValueError('Invalid fixup extent')
        blob=data[offset:offset+length]
        version,starts,imports,symbols,count,kind,compression=struct.unpack_from('<7I',blob)
        if version or compression or kind not in (1,2,3):raise ValueError('Unsupported fixup/import/symbol format')
        stride={1:4,2:8,3:16}[kind]
        if imports>len(blob) or count>(len(blob)-imports)//stride or symbols>len(blob):raise ValueError('Invalid import/string extent')
        formats[str(kind)]+=count;audited.append(image.record['host'])
        for i in range(count):
            at=imports+i*stride
            packed=struct.unpack_from('<Q' if kind==3 else '<I',blob,at)[0]
            if kind==3:
                if (packed>>17)&0x7fff:raise ValueError('Reserved import bits set')
                ordinal=packed&0xffff;ordinal=ordinal-65536 if ordinal>65520 else ordinal
                weak=bool(packed&0x10000);name_offset=packed>>32
            else:
                ordinal=packed&255;ordinal=ordinal-256 if ordinal>240 else ordinal
                weak=bool(packed&256);name_offset=packed>>9
            start=symbols+name_offset
            if start>=len(blob):raise ValueError('Import name outside symbols')
            end=blob.index(0,start);name=blob[start:end].decode();checked+=1
            if not name:raise ValueError('Empty import name')
            if ordinal<0:special[str(ordinal)]+=1;continue
            if ordinal>len(image.dependencies):raise ValueError('Import ordinal exceeds dependency count')
            expected=image.dependencies[ordinal-1] if ordinal else image.install_name
            target=provider(expected) if ordinal else image
            if exported(target,name):continue
            key=(image.record['image'],expected,name,weak)
            missing[key]={'consumer':key[0],'provider':expected,'symbol':name,'weak_import':weak,
                'provider_in_inventory':target is not None,'evidence':'chained import table; used pointer slots not checked'}
    except (ValueError,IndexError,struct.error) as error:
        gaps.append({'host':image.record['host'],'reason':str(error)})
rows=sorted(missing.values(),key=lambda r:(r['weak_import'],r['consumer'],r['symbol']))
report={'checked_at':datetime.now(timezone.utc).isoformat(),'scope':__doc__,
 'inventory':str(args.inventory),'images':len(images),'chained_images_audited':audited,
 'import_table_records_checked':checked,'import_formats':dict(formats),'unresolved_candidates':rows,
 'unsupported_images':gaps,'special_lookup_ordinals_not_audited':dict(special),
 'image_sha256':{i.record['host']:i.host_sha256 for i in images},'full_compatibility':False}
args.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'images':len(images),'import_records':checked,'unresolved_candidates':dict(Counter(
 'weak' if r['weak_import'] else 'strong' for r in rows)),'unsupported_images':len(gaps)}))
