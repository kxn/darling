#!/usr/bin/env python3
"""Pin missing graphics CFString imports to their actual original values."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,runpy,struct,subprocess
root=Path(__file__).resolve().parent.parent
d=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={
    'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
manifest_path=root/'config/cache-image-pins.json';manifest=json.loads(manifest_path.read_text())
constants_path=root/'config/native-string-constants.json';constants=json.loads(constants_path.read_text())
existing={r['symbol']:r for r in constants['constants']}
existing_extra={r['symbol']:r for r in constants.get('extra_identifiers',[])}
providers={}
for framework,prefix in [('CoreVideo','_kCV'),('CoreGraphics','_kCG'),('CoreImage','_kCI'),('ImageIO','_kCG')]:
    provider=f'/System/Library/Frameworks/{framework}.framework/Versions/A/{framework}'
    original=root/'runtime/fullsystem-libraries'/provider.lstrip('/')
    backend=root/'runtime/rootfs/usr/libexec/darling'/provider.lstrip('/')
    listing=subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(backend)],text=True)
    providers[provider]=dict(prefix=prefix,sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
        original_backend_sha256=hashlib.sha256(backend.read_bytes()).hexdigest(),
        old_exports=set(re.findall(r'^(?:0x[\da-fA-F]+|\[re-export\])\s+(\S+)',listing,re.M)))
isa=d['resolve']('/System/Library/Frameworks/CoreFoundation.framework/Versions/A/CoreFoundation','___CFConstantStringClassReference')
records=[];typed=[];unclassified=[]
for target in ['quartzcore-native','symbolication-native','core-symbolication-native']:
    pin=manifest[target];path=root/'runtime/fullsystem-libraries'/pin['path'].lstrip('/')
    data=path.read_bytes();assert hashlib.sha256(data).hexdigest()==pin['sha256']
    image=d['image'](pin['path']);cursor=32
    for _ in range(struct.unpack_from('<I',data,16)[0]):
        command,size=struct.unpack_from('<II',data,cursor)
        if command==2:symoff,count,stroff,strsize=struct.unpack_from('<IIII',data,cursor+8)
        cursor+=size
    for index in range(count):
        at=symoff+16*index;nameoff,kind,section,desc,value=struct.unpack_from('<IBBHQ',data,at)
        ordinal=desc>>8
        if kind&14 or not kind&1 or not 0<ordinal<=len(image.dependencies):continue
        provider=image.dependencies[ordinal-1]
        if provider not in providers:continue
        provider_info=providers[provider]
        name=data[stroff+nameoff:data.index(0,stroff+nameoff)].decode()
        if name in provider_info['old_exports'] or not name.startswith(provider_info['prefix']):continue
        slot=d['resolve'](provider,name);assert slot is not None
        obj=d['pointer'](slot)
        try:object_isa=d['pointer'](obj)
        except ValueError:object_isa=None
        if object_isa!=isa:
            record=existing_extra.get(name)
            if record and record['provider']==provider and record['kind'] in ('double','int32'):
                assert record['provider_sha256']==provider_info['sha256']
                width={'double':8,'int32':4}[record['kind']]
                assert len(bytes.fromhex(record['bytes']))==width and d['read'](slot,width).hex()==record['bytes']
                typed.append(dict(consumer=target,**record))
                manifest[target]['import_providers'][name]='/usr/lib/libDarlingNativeConstants.dylib'
                continue
            unclassified.append(dict(consumer=target,provider=provider,symbol=name,slot=hex(slot),
                raw_value=hex(obj),implemented=False,reason='Not a verified constant CFString; needs a separate typed ABI implementation.'))
            continue
        flags=struct.unpack('<Q',d['read'](obj+8,8))[0];assert flags&255==0xc8
        length=struct.unpack('<Q',d['read'](obj+24,8))[0];assert 0<length<4096
        text=d['read'](d['pointer'](obj+16),length).decode('ascii')
        record=dict(symbol=name,provider=provider,provider_sha256=provider_info['sha256'],value=text,
            object_flags=hex(flags),object_address=hex(obj),slot_address=hex(slot))
        if name in existing:
            assert all(existing[name][key]==record[key] for key in record)
        else:constants['constants'].append(record);existing[name]=record
        manifest[target]['import_providers'][name]='/usr/lib/libDarlingNativeConstants.dylib'
        records.append(dict(consumer=target,**record))
constants_path.write_text(json.dumps(constants,indent=2)+'\n')
manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),native_execution=False,
    providers={p:{k:v for k,v in info.items() if k!='old_exports'} for p,info in providers.items()},
    imports=records,unique_missing_identifiers=len({r['symbol'] for r in records}),
    unclassified_typed_imports=unclassified,
    typed_imports=typed,
    total_compat_cfstrings=len(constants['constants']),
    provider_operations_implemented=False,
    scope='Typed original CFString pointer/value imports only. Reuse the existing constants library; no graphics, color conversion, pixel-buffer or display API added. Non-CFString symbols remain explicitly unimplemented.')
(root/'artifacts/quartzcore-native-constants-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print('Pinned original missing graphics CFString imports:',len(records),'unclassified:',len(unclassified))
