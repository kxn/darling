#!/usr/bin/env python3
"""Select the real Foundation shim and class rather than duplicate implementations."""
from pathlib import Path
from datetime import datetime,timezone
import fcntl,hashlib,json,runpy,subprocess,shutil,re
root=Path(__file__).resolve().parent.parent;digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
pins=json.loads((root/'config/cache-image-pins.json').read_text());pin=pins['swift-foundation-shim-native'];original='runtime/fullsystem-libraries'+pin['path'];source='runtime/rebuilt-swift-foundation-shim-native/libswiftFoundation.dylib';report='runtime/rebuilt-swift-foundation-shim-native/reconstruction.json';r=json.loads((root/report).read_text())
assert digest(original)==pin['sha256']==r['original_image_sha256'] and digest(source)==r['staged_image_sha256'];assert r['exports']==2 and not r['redirected_imports'] and not r['backend_call_overrides']
build=root/'runtime/foundation-coherent';libraries=build/'libraries';libraries.mkdir(parents=True,exist_ok=True);sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
anchor=build/'float-anchor.c';anchor.write_text('static const unsigned char anchor __attribute__((used)) = 0;\n')
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-c',str(anchor),'-o',str(build/'float-anchor.o')],check=True)
base='runtime/foundation-coherent/float-base.dylib';subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-lSystem','-headerpad','0x1000','-install_name','/usr/lib/libDarlingConstantFloat.dylib',str(build/'float-anchor.o'),'-o',str(root/base)],check=True)
foundation='runtime/foundation-native-framework-stage/Foundation.framework/Versions/C/Foundation';names=['_OBJC_CLASS_$_NSConstantFloatNumber','_OBJC_METACLASS_$_NSConstantFloatNumber','_OBJC_IVAR_$_NSConstantFloatNumber._value'];exports=subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(root/foundation)],text=True);assert all(n in exports for n in names)
payload,changes=runpy.run_path(str(root/'scripts/macho-named-reexport.py'))['add']((root/base).read_bytes(),'/System/Library/Frameworks/Foundation.framework/Versions/C/Foundation',names)
helper='runtime/foundation-coherent/libraries/libDarlingConstantFloat.dylib';shim='runtime/foundation-coherent/libraries/libswiftFoundation.dylib'
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);pending=root/(helper+'.pending');pending.write_bytes(payload);pending.replace(root/helper);pending=root/(shim+'.pending');shutil.copyfile(root/source,pending);pending.replace(root/shim)
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),shim=dict(original=original,original_sha256=digest(original),source=source,source_sha256=digest(source),library=shim,library_sha256=digest(shim),reconstruction=report,reconstruction_sha256=digest(report),exports=2),float_class=dict(base=base,base_sha256=digest(base),library=helper,library_sha256=digest(helper),provider=foundation,provider_sha256=digest(foundation),names=names,export_changes=changes),installed=False,runtime_execution_verified=False,scope='Actual current Intel libswiftFoundation forwarding image (no Swift or ObjC class definitions), plus an explicit reexport of the native Foundation float class/metadata instead of defining a second class. Old compatibility libraries and guards are unchanged outside this private profile. Class layout and behavior require runtime verification.')
(root/'artifacts/foundation-coherent-stage.json').write_text(json.dumps(record,indent=2)+'\n');print('Staged native Swift Foundation shim and single native constant-float class')
