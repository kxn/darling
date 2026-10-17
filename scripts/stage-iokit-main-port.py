#!/usr/bin/env python3
"""Incrementally compile Darling's new default-port constant into the experiment."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
config=json.loads((root/'config/iokit-main-port.json').read_text())
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
repo=root/'vendor/darling/src/external/IOKitUser'
if subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()!=config['source_commit']:
    raise ValueError('Changed IOKitUser base source')
source=repo/'IOKitLib.c';header=repo/'IOKitLib.h'
definition=re.findall(r'^const mach_port_t kIOMainPortDefault = MACH_PORT_NULL;$',source.read_text(),re.M)
if len(definition)!=1 or 'extern const mach_port_t kIOMainPortDefault;' not in header.read_text():
    raise ValueError('Missing reviewed Darling constant declaration/definition')
ns=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={
    'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
native=root/'runtime/fullsystem-libraries'/config['provider'].lstrip('/')
if digest(native)!=config['provider_sha256'] or ns['resolve'](config['provider'],config['symbol'])!=int(config['address'],0):
    raise ValueError('Changed native constant provider')
if ns['read'](int(config['address'],0),4).hex()!=config['bytes'] or config['bytes']!='00000000':
    raise ValueError('Changed default-port sentinel')
backend=root/config['backend']
if digest(backend)!=config['backend_sha256']:raise ValueError('Changed original IOKit')
build=root/'runtime/iokit-main-port';build.mkdir(exist_ok=True)
component=build/'main-port.c';component.write_text('#include <mach/mach.h>\n'+definition[0]+'\n')
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
obj=build/'main-port.o'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-c',str(component),'-o',str(obj)],check=True)
copy=root/'runtime/foundation-native-library-stage/libDarlingIOKitBackend.dylib'
temporary=copy.with_name(copy.name+'.pending');temporary.write_bytes(backend.read_bytes())
subprocess.run(['python3',str(root/'scripts/macho-set-id.py'),str(temporary),'/usr/lib/libDarlingIOKitBackend.dylib'],check=True)
temporary.replace(copy)
framework_root=root/'runtime/foundation-native-framework-stage/IOKit.framework'
output=framework_root/'Versions/A/IOKit';output.parent.mkdir(parents=True,exist_ok=True)
temporary=output.with_name(output.name+'.pending');guest=root/'runtime/rootfs/usr/libexec/darling'
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11',
    '-syslibroot',str(guest),'-lSystem','-install_name',config['provider'],
    '-compatibility_version','1.0.0','-current_version','275.0.0',
    '-reexport_library',str(copy),str(obj),'-o',str(temporary)],check=True)
temporary.replace(output)
for link,target in [(framework_root/'Versions/Current','A'),(framework_root/'IOKit','Versions/Current/IOKit')]:
    if link.exists() or link.is_symlink():link.unlink()
    link.symlink_to(target)
if digest(backend)!=config['backend_sha256']:raise ValueError('Original IOKit changed')
(root/'artifacts/iokit-main-port.json').write_text(json.dumps(dict(
    staged_at=datetime.now(timezone.utc).isoformat(),installed=False,full_darling_rebuild=False,
    native_reference=config,source_sha256=digest(source),header_sha256=digest(header),
    stage_framework=str(output.relative_to(root)),stage_framework_sha256=digest(output),
    stage_backend=str(copy.relative_to(root)),stage_backend_sha256=digest(copy),
    original_backend_unchanged=True,scope='One actual default-port sentinel from the changed Darling IOKit source; all IOKit operations remain with the existing backend. No hardware/driver/service capability added.'),indent=2)+'\n')
print('Staged Darling IOKit default-port constant; original framework unchanged')
