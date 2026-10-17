#!/usr/bin/env python3
"""Create independent read-only cache metadata expectations and a fixture root."""
from pathlib import Path
import hashlib,json,os,runpy,struct

root=Path(__file__).resolve().parent.parent
ns=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={
 'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
 'REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
h=ns['cache']['contexts'][0].header
name='/System/Library/Frameworks/Foundation.framework/Versions/C/Foundation';image=ns['image'](name)
header=ns['read'](image.base,32);count,length=struct.unpack_from('<II',header,16)
data=ns['read'](image.base+32,length);cursor=0;uuid=None
for _ in range(count):
    command,size=struct.unpack_from('<II',data,cursor)
    if command==0x1b:uuid=data[cursor+8:cursor+24]
    cursor+=size
if uuid is None:raise ValueError('No original image UUID')
with (root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h').open('rb') as source:
    cache_uuid=source.read(104)[88:104]
    source.seek(h.imagesTextOffset);text_entries=source.read(h.imagesTextCount*32)
image_uuids=[];has_names=[]
for i in range(h.imagesTextCount):
    identity,address,_,_=struct.unpack_from('<16sQII',text_entries,i*32)
    image_uuids.append(identity)
    mach=ns['read'](address,32);commands,extent=struct.unpack_from('<II',mach,16)
    payload=ns['read'](address+32,extent);cursor=0;has_name=False;actual_uuid=None
    for _ in range(commands):
        command,size=struct.unpack_from('<II',payload,cursor)
        has_name|=command==13
        if command==27:actual_uuid=payload[cursor+8:cursor+24]
        cursor+=size
    if actual_uuid!=identity:raise ValueError('Image UUID table/header disagreement')
    has_names.append(has_name)
build=root/'runtime/dyld-cache-introspection';build.mkdir(exist_ok=True)
segments=[{'name':name,'address':address,'size':size} for name,address,size,_,_ in image.segments]
oracle={'cache_uuid':cache_uuid.hex(),'base':h.sharedRegionStart,'size':h.sharedRegionSize,
 'images':h.imagesTextCount,'files':1+h.subCacheArrayCount,'image_name':name,'image_uuid':uuid.hex(),
 'segments':segments,'prefix':ns['read'](image.base,64).hex()}
oracle['image_uuid_table_sha256']=hashlib.sha256(b''.join(image_uuids)).hexdigest()
oracle['images_without_installname']=has_names.count(False)
(build/'oracle.json').write_text(json.dumps(oracle,indent=2)+'\n')
lines=['#include <stdint.h>','#define CACHE_BASE UINT64_C('+str(h.sharedRegionStart)+')',
 '#define CACHE_SIZE UINT64_C('+str(h.sharedRegionSize)+')','#define CACHE_IMAGES '+str(h.imagesTextCount),
 '#define CACHE_FILES '+str(oracle['files']),'#define SELECTED_IMAGE '+json.dumps(name)]
for name,payload in [('cache_uuid',cache_uuid),('image_uuid',uuid),('image_prefix',ns['read'](image.base,64))]:
    lines.append('static const unsigned char '+name+'[]={'+','.join(str(b) for b in payload)+'};')
lines.append('static const unsigned char expected_image_uuids[][16]={')
for identity in image_uuids:lines.append('{'+','.join(str(b) for b in identity)+'},')
lines.append('};')
lines.append('static const unsigned char expected_image_has_name[]={'+','.join(str(int(b)) for b in has_names)+'};')
lines+=['struct ExpectedSegment { const char *name; uint64_t address,size; };',
 'static const struct ExpectedSegment expected_segments[]={']
for segment in segments:
    lines.append('{'+json.dumps(segment['name'])+','+str(segment['address'])+'ULL,'+str(segment['size'])+'ULL},')
lines.append('};');(build/'oracle.h').write_text('\n'.join(lines)+'\n')
parent=root/'runtime/dyld-introspection-fixture/System/Library';parent.mkdir(parents=True,exist_ok=True)
for destination in [parent/'dyld',parent/'Caches/com.apple.dyld']:
    destination.parent.mkdir(parents=True,exist_ok=True)
    target=os.path.relpath(root/'runtime/fullsystem/intel-cache',destination.parent)
    if destination.is_symlink():
        if os.readlink(destination)!=target:raise ValueError('Unexpected cache fixture symlink')
    elif destination.exists():raise ValueError('Refusing to replace cache fixture directory')
    else:destination.symlink_to(target)
(root/'runtime/dyld-introspection-empty').mkdir(exist_ok=True)
(build/'invalid-cache').write_bytes(b'dyld_v1 x86_64h\0'+bytes(4080))
# Header/array-only sparse copies exercise incomplete split sets without
# copying or modifying any of the genuine multi-gigabyte cache inputs.
primary=root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h'
prefix_length=max(h.imagesTextOffset+h.imagesTextCount*32,h.subCacheArrayOffset+h.subCacheArrayCount*56)
with primary.open('rb') as source:prefix=source.read(prefix_length)
def sparse_copy(destination,payload,length):
    destination.parent.mkdir(parents=True,exist_ok=True)
    if not destination.resolve().is_relative_to(build.resolve()) or destination.is_symlink():
        raise ValueError('Unexpected negative fixture path')
    if destination.exists() and destination.stat().st_nlink!=1:raise ValueError('Refusing a shared negative fixture inode')
    with destination.open('wb') as output:output.write(payload);output.truncate(length)
for directory in ['missing-subcache','wrong-subcache-uuid']:
    sparse_copy(build/directory/primary.name,prefix,primary.stat().st_size)
child=Path(str(primary)+'.01')
with child.open('rb') as source:child_prefix=bytearray(source.read(4096))
child_prefix[88]^=1
sparse_copy(build/'wrong-subcache-uuid'/(primary.name+'.01'),child_prefix,child.stat().st_size)
