#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import fcntl,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent;digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
analysis=json.loads((root/'artifacts/imageio-cg-constants-analysis.json').read_text());source=analysis['source'];assert digest(source)==analysis['source_sha256']
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';build=root/'runtime/imageio-cg-constants';lib=build/'libraries';lib.mkdir(parents=True,exist_ok=True)
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-c',str(root/source),'-o',str(build/'constants.o')],check=True)
helper='runtime/imageio-cg-constants/libraries/libDarlingImageIOCGConstants.dylib';pending=root/(helper+'.pending');subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-framework','CoreFoundation','-install_name','/usr/lib/libDarlingImageIOCGConstants.dylib',str(build/'constants.o'),'-o',str(pending)],check=True)
base='runtime/native-layer-support/frameworks/CoreGraphics.framework/Versions/A/CoreGraphics';old=json.loads((root/'artifacts/native-layer-support-stage.json').read_text());assert digest(base)==old['library_sha256']
payload,changes=runpy.run_path(str(root/'scripts/macho-named-reexport.py'))['add']((root/base).read_bytes(),'/usr/lib/libDarlingImageIOCGConstants.dylib',list(analysis['constants']))
output='runtime/imageio-cg-constants/frameworks/CoreGraphics.framework/Versions/A/CoreGraphics';target=root/output;target.parent.mkdir(parents=True,exist_ok=True)
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);pending.replace(root/helper);temp=target.with_suffix('.pending');temp.write_bytes(payload);temp.replace(target)
f=target.parent.parent.parent
for p,v in [(f/'Versions/Current','A'),(f/'CoreGraphics','Versions/Current/CoreGraphics')]:
 if not p.is_symlink():p.symlink_to(v)
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),base=base,base_sha256=digest(base),source=source,source_sha256=digest(source),helper=helper,helper_sha256=digest(helper),library=output,library_sha256=digest(output),analysis='artifacts/imageio-cg-constants-analysis.json',analysis_sha256=digest('artifacts/imageio-cg-constants-analysis.json'),export_changes=changes,constant_count=len(analysis['constants']),installed=False,runtime_execution_verified=False)
(root/'artifacts/imageio-cg-constants-stage.json').write_text(json.dumps(record,indent=2)+'\n');print('Staged',len(analysis['constants']),'original-value source CFString variables')
