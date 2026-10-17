#!/usr/bin/env python3
"""Stage the full original Intel MobileGestalt with its actual device context."""
from pathlib import Path
import fcntl,hashlib,json,shutil
root=Path(__file__).resolve().parent.parent
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
pin=json.loads((root/'config/cache-image-pins.json').read_text())['mobilegestalt-native'];build='runtime/rebuilt-mobilegestalt-native';report=json.loads((root/(build+'/reconstruction.json')).read_text())
assert digest('runtime/fullsystem-libraries'+pin['path'])==pin['sha256']==report['original_image_sha256']
source=build+'/libMobileGestalt.dylib';assert digest(source)==report['staged_image_sha256'] and not report['backend_call_overrides'] and not report['redirected_imports']
assert set(report['objc_metadata']['classes'])=={'MGIOKitHelper','OS_MobileGestalt'}
library='runtime/mobilegestalt-native/libraries/libMobileGestalt.dylib';target=root/library;target.parent.mkdir(parents=True,exist_ok=True)
dependency='runtime/rebuilt-iomobileframebuffer-native/IOMobileFramebuffer';dreport='runtime/rebuilt-iomobileframebuffer-native/reconstruction.json';d=json.loads((root/dreport).read_text());dpin=json.loads((root/'config/cache-image-pins.json').read_text())['iomobileframebuffer-native']
assert digest(dependency)==d['staged_image_sha256'] and d['original_image_sha256']==dpin['sha256'] and not d['backend_call_overrides']
assert set(d['redirected_imports'])=={'__ZdlPvSt19__type_descriptor_t','__ZnwmSt19__type_descriptor_t'}
framework='runtime/mobilegestalt-native/frameworks/IOMobileFramebuffer.framework/Versions/A/IOMobileFramebuffer';frame=root/framework;frame.parent.mkdir(parents=True,exist_ok=True)
oah_source='runtime/rebuilt-oah-native/liboah.dylib';oah_report='runtime/rebuilt-oah-native/reconstruction.json';oah=json.loads((root/oah_report).read_text());oah_pin=json.loads((root/'config/cache-image-pins.json').read_text())['oah-native']
assert digest(oah_source)==oah['staged_image_sha256'] and oah['original_image_sha256']==oah_pin['sha256'] and not oah['backend_call_overrides']
assert set(oah['redirected_imports'])==set(oah_pin['import_providers']) and set(oah['redirected_imports'])<=set(d['redirected_imports'])
oah_library='runtime/mobilegestalt-native/libraries/liboah.dylib'
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);pending=target.with_suffix('.pending');shutil.copyfile(root/source,pending);pending.replace(target)
 pending=frame.with_suffix('.pending');shutil.copyfile(root/dependency,pending);pending.replace(frame)
 pending=root/(oah_library+'.pending');shutil.copyfile(root/oah_source,pending);pending.replace(root/oah_library)
base=frame.parent.parent.parent
for path,value in [(base/'Versions/Current','A'),(base/'IOMobileFramebuffer','Versions/Current/IOMobileFramebuffer')]:
 if not path.is_symlink():path.symlink_to(value)
record=dict(original=pin,source=source,source_sha256=digest(source),library=library,library_sha256=digest(library),reconstruction=build+'/reconstruction.json',reconstruction_sha256=digest(build+'/reconstruction.json'),objc_classes=report['objc_metadata']['classes'],installed=False,runtime_execution_verified=False,
 dependency=dict(original=dpin,source=dependency,source_sha256=digest(dependency),library=framework,library_sha256=digest(framework),reconstruction=dreport,reconstruction_sha256=digest(dreport)),
 oah_dependency=dict(original=oah_pin,source=oah_source,source_sha256=digest(oah_source),library=oah_library,library_sha256=digest(oah_library),reconstruction=oah_report,reconstruction_sha256=digest(oah_report)),
 typed_cpp_adapter=dict(library='runtime/rebuilt-der/libDarlingDER.dylib',library_sha256=digest('runtime/rebuilt-der/libDarlingDER.dylib'),source='scripts/der-allocation-compat.cpp',source_sha256=digest('scripts/der-allocation-compat.cpp'),names=d['redirected_imports'],scope='Existing legacy allocator adapters preserve real standard new/delete behavior; type-tag isolation is absent.'),
 scope='Full original Intel code and actual MGIOKitHelper/OS_MobileGestalt classes, restored cache relocations/selectors and normal dependencies. No replacement persona/device object, backend-call override or invented hardware answer.')
(root/'artifacts/mobilegestalt-native-stage.json').write_text(json.dumps(record,indent=2)+'\n');print('Staged full original Intel MobileGestalt and two original classes')
