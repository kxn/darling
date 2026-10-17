#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import fcntl,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent;digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest();build=root/'runtime/imageio-legacy-key';(build/'libraries').mkdir(parents=True,exist_ok=True)
source='vendor/darling/src/frameworks/ImageIO/src/CGImageLegacyConstants.c';sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-c',str(root/source),'-o',str(build/'constant.o')],check=True)
helper='runtime/imageio-legacy-key/libraries/libDarlingImageIOLegacyKey.dylib';pending=root/(helper+'.pending');subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-framework','CoreFoundation','-install_name','/usr/lib/libDarlingImageIOLegacyKey.dylib',str(build/'constant.o'),'-o',str(pending)],check=True)
base='runtime/imageio-native/frameworks/ImageIO.framework/Versions/A/ImageIO';stage=json.loads((root/'artifacts/imageio-native-stage.json').read_text());assert digest(base)==stage['entries'][0]['library_sha256']
payload,changes=runpy.run_path(str(root/'scripts/macho-named-reexport.py'))['add']((root/base).read_bytes(),'/usr/lib/libDarlingImageIOLegacyKey.dylib',['_kCGImageDestinationDPI']);output='runtime/imageio-legacy-key/frameworks/ImageIO.framework/Versions/A/ImageIO';target=root/output;target.parent.mkdir(parents=True,exist_ok=True)
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);pending.replace(root/helper);temp=target.with_suffix('.pending');temp.write_bytes(payload);temp.replace(target)
f=target.parent.parent.parent
for p,v in [(f/'Versions/Current','A'),(f/'ImageIO','Versions/Current/ImageIO')]:
 if not p.is_symlink():p.symlink_to(v)
# Resource libraries retain their actual original ImageIO-relative locations.
resource=f/'Versions/A/Resources'
if not resource.is_symlink():resource.symlink_to(root/'runtime/imageio-native/frameworks/ImageIO.framework/Versions/A/Resources',target_is_directory=True)
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),base=base,base_sha256=digest(base),source=source,source_sha256=digest(source),helper=helper,helper_sha256=digest(helper),library=output,library_sha256=digest(output),export_changes=changes,installed=False,runtime_execution_verified=False,scope='Preserves the sole old Darling-only ImageIO export required by existing AppKit. Its key bytes are unchanged; native image destination DPI option translation is not implemented.')
(root/'artifacts/imageio-legacy-key-stage.json').write_text(json.dumps(record,indent=2)+'\n');print('Preserved existing Darling AppKit ImageIO DPI constant')
