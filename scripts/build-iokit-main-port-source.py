#!/usr/bin/env python3
"""Build the actual IOMainPort source entry while retaining the existing backend."""
from pathlib import Path
import fcntl,hashlib,json,re,subprocess
root=Path(__file__).resolve().parent.parent;digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
repo=root/'vendor/darling/src/external/IOKitUser';source='vendor/darling/src/external/IOKitUser/IOMainPort.c'
config=json.loads((root/'config/iokit-main-port.json').read_text());backend='runtime/foundation-native-library-stage/libDarlingIOKitBackend.dylib';old=json.loads((root/'artifacts/iokit-main-port.json').read_text())
assert digest(backend)==old['stage_backend_sha256']
reference='logs/iokit-original-main-port-disassembly.log';text=(root/reference).read_text();at=text.index('_IOMainPort:');assert 'jmp\t_IOMasterPort' in text[at:at+300]
base=root/'runtime/iokit-main-port-source';base.mkdir(exist_ok=True)
constant=base/'constant.c';definition=re.findall(r'^const mach_port_t kIOMainPortDefault = MACH_PORT_NULL;$',(repo/'IOKitLib.c').read_text(),re.M);assert len(definition)==1;constant.write_text('#include <mach/mach.h>\n'+definition[0]+'\n')
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
for name,path in [('main',root/source),('constant',constant)]:
 subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-Wno-deprecated-declarations','-c',str(path),'-o',str(base/(name+'.o'))],check=True)
framework=base/'frameworks/IOKit.framework';output=framework/'Versions/A/IOKit';output.parent.mkdir(parents=True,exist_ok=True)
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 pending=output.with_suffix('.pending')
 subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(root/'runtime/rootfs/usr/libexec/darling'),'-lSystem','-install_name',config['provider'],'-compatibility_version','1.0.0','-current_version','275.0.0','-reexport_library',str(root/backend),str(base/'main.o'),str(base/'constant.o'),'-o',str(pending)],check=True)
 pending.replace(output)
 for path,destination in [(framework/'Versions/Current','A'),(framework/'IOKit','Versions/Current/IOKit')]:
  if not path.is_symlink():path.symlink_to(destination)
record=dict(source=source,source_sha256=digest(source),source_header='vendor/darling/src/external/IOKitUser/IOKitLib.h',source_header_sha256=digest('vendor/darling/src/external/IOKitUser/IOKitLib.h'),source_list='vendor/darling/src/external/IOKitUser/CMakeLists.txt',source_list_sha256=digest('vendor/darling/src/external/IOKitUser/CMakeLists.txt'),native_disassembly=reference,native_disassembly_sha256=digest(reference),native_image='runtime/fullsystem-libraries/System/Library/Frameworks/IOKit.framework/Versions/A/IOKit',native_image_sha256=digest('runtime/fullsystem-libraries/System/Library/Frameworks/IOKit.framework/Versions/A/IOKit'),framework=str(output.relative_to(root)),framework_sha256=digest(str(output.relative_to(root))),backend=backend,backend_sha256=digest(backend),constant_source=str(constant.relative_to(root)),constant_source_sha256=digest(str(constant.relative_to(root))),full_IOKit_source_build=False,source_component='Actual new entry point, original default-port sentinel, and unchanged existing IOKit backend',runtime_execution_verified=False)
(root/'artifacts/iokit-main-port-source-build.json').write_text(json.dumps(record,indent=2)+'\n');print('Compiled source IOMainPort with original backend; no fabricated port or success')
