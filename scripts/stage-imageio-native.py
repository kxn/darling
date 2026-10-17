#!/usr/bin/env python3
"""Stage complete original ImageIO, codecs and direct original dependencies."""
from pathlib import Path
from datetime import datetime,timezone
import fcntl,hashlib,json,shutil
root=Path(__file__).resolve().parent.parent;pins=json.loads((root/'config/cache-image-pins.json').read_text());digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
names=['imageio-native','apple-jpeg-native','colorsync-native','iosurface-accelerator-native','ate-native']+['imageio-'+s.lower()+'-native' for s in ['Png','TIFF','GIF','JP2','JPEG','Radiance']]
base='runtime/imageio-native';entries=[]
for name in names:
 pin=pins[name];original='runtime/fullsystem-libraries'+pin['path'];report='runtime/rebuilt-'+name+'/reconstruction.json';r=json.loads((root/report).read_text());source='runtime/rebuilt-'+name+'/'+Path(pin['path']).name
 assert digest(original)==pin['sha256']==r['original_image_sha256'];assert digest(source)==r['staged_image_sha256'];assert not r['backend_call_overrides'];assert set(r['redirected_imports'])==set(pin.get('import_providers',{}));assert all(v=='/usr/lib/libDarlingDER.dylib' for v in pin.get('import_providers',{}).values())
 if name.startswith('imageio-') and name!='imageio-native':relative='ImageIO.framework/Versions/A/Resources/'+Path(pin['path']).name
 elif '.framework/' not in pin['path']:relative=None
 else:relative=pin['path'].split('/Frameworks/',1)[1] if '/Frameworks/' in pin['path'] else pin['path'].split('/PrivateFrameworks/',1)[1]
 output=base+'/frameworks/'+relative if relative is not None else base+'/libraries/'+Path(pin['path']).name;entries.append(dict(target=name,original=original,original_sha256=digest(original),source=source,source_sha256=digest(source),reconstruction=report,reconstruction_sha256=digest(report),library=output,library_sha256=digest(source),exports=r['exports'],typed_cpp_redirects=r['redirected_imports'],objc_classes=r.get('objc_metadata',{}).get('classes',[])))
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 for e in entries:
  target=root/e['library'];target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_suffix(target.suffix+'.pending');shutil.copyfile(root/e['source'],temp);temp.replace(target)
  if e['target'].startswith('imageio-') and e['target']!='imageio-native':
   target=root/(base+'/libraries/'+Path(e['source']).name);target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_suffix(target.suffix+'.pending');shutil.copyfile(root/e['source'],temp);temp.replace(target)
 for name in ['ImageIO','AppleJPEG','ColorSync','IOSurfaceAccelerator']:
  f=root/(base+'/frameworks/'+name+'.framework')
  for p,value in [(f/'Versions/Current','A'),(f/name,'Versions/Current/'+name)]:
   if not p.is_symlink():p.symlink_to(value)
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),entries=entries,installed=False,runtime_execution_verified=False,typed_cpp_adapter=dict(library='runtime/rebuilt-der/libDarlingDER.dylib',library_sha256=digest('runtime/rebuilt-der/libDarlingDER.dylib'),source='scripts/der-allocation-compat.cpp',source_sha256=digest('scripts/der-allocation-compat.cpp')),scope='Full original Intel ImageIO and ten actual codec/dependency images. Original code, CF source objects, codec parsing and metadata operations are retained; zero backend-call overrides. Explicit typed C++ new/delete imports use the existing real standard allocation fallback; no type-tag isolation. No success/empty-property substitute is provided. Runtime compatibility remains unverified until probes pass.')
(root/'artifacts/imageio-native-stage.json').write_text(json.dumps(record,indent=2)+'\n');print('Staged original ImageIO and ten dependencies')
