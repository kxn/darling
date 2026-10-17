#!/usr/bin/env python3
"""Recover original CFString variables needed by ImageIO's strong bindings."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,struct,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h','REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
exports=set()
for path in ['runtime/native-layer-support/frameworks/CoreGraphics.framework/Versions/A/CoreGraphics','runtime/foundation-native-library-stage/libDarlingCoreGraphicsBackend.dylib']:
 t=subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(root/path)],text=True)
 for line in t.splitlines():
  if line.startswith(('0x','[re-export]')):exports.add(line.split()[1])
t=subprocess.check_output(['llvm-objdump-19','--macho','--bind',str(root/'runtime/rebuilt-imageio-native/ImageIO')],text=True)
names=sorted({x.split()[-1] for x in t.splitlines() if 'CoreGraphics' in x and x.split()[-1] not in exports})
records={};strings=[];provider='/System/Library/Frameworks/CoreGraphics.framework/Versions/A/CoreGraphics'
for name in names:
 assert name.startswith('_k');address=m['resolve'](provider,name);obj=m['pointer'](address);flags=struct.unpack('<I',m['read'](obj+8,4))[0];assert flags==0x7c8
 n=struct.unpack('<Q',m['read'](obj+24,8))[0];assert 0<n<512
 text=m['read'](m['pointer'](obj+16),n).decode('ascii');records[name]=dict(address=hex(address),object_address=hex(obj),value=text)
 strings.append('const CFStringRef '+name[1:]+' = CFSTR('+json.dumps(text)+');')
source='vendor/darling/src/external/cocotron/CoreGraphics/CGImageIOConstants.c';(root/source).write_text('// Exact CoreGraphics CFString values consumed by original ImageIO.\n// Provenance: artifacts/imageio-cg-constants-analysis.json. No provider backend is implied.\n#include <CoreFoundation/CoreFoundation.h>\n\n'+'\n'.join(strings)+'\n')
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),provider=provider,provider_sha256=digest('runtime/fullsystem-libraries'+provider),constants=records,source=source,source_sha256=digest(source),scope='Exact pointer-variable ABI and original CFString bytes. These keys do not implement private image-provider/block or tone-mapping backends.')
(root/'artifacts/imageio-cg-constants-analysis.json').write_text(json.dumps(report,indent=2)+'\n');print('Recovered',len(records),'actual CoreGraphics CFString constants')
