#!/usr/bin/env python3
"""Expose the exact original ContainerManager API imported by LaunchServices."""
from pathlib import Path
import fcntl,hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
digest=lambda s:hashlib.sha256((root/s).read_bytes()).hexdigest()
base='runtime/sysdir-native-export/libraries/libSystem.B.dylib'
old=json.loads((root/'artifacts/sysdir-native-export-stage.json').read_text());assert digest(base)==old['library_sha256']
pin=json.loads((root/'config/cache-image-pins.json').read_text())['containermanager-native']
original='runtime/fullsystem-libraries'+pin['path'];assert digest(original)==pin['sha256']
provider='runtime/foundation-native-library-stage/libsystem_containermanager.dylib'
reconstruction=json.loads((root/'runtime/rebuilt-containermanager-native/reconstruction.json').read_text())
assert reconstruction['original_image_sha256']==pin['sha256'] and digest(provider)==reconstruction['staged_image_sha256']
client='runtime/native-framework-stage/LaunchServices.framework/Versions/A/LaunchServices'
imports=subprocess.check_output(['llvm-nm-19','-u',str(root/client)],text=True)
names=sorted(set(re.findall(r'^(_container_\S+)$',imports,re.M)));assert len(names)==17,names
api=runpy.run_path(str(root/'scripts/macho-named-reexport.py'))
exports=subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(root/provider)],text=True)
available=set(re.findall(r'^0x[0-9A-Fa-f]+\s+(\S+)',exports,re.M));assert set(names)<=available
subprocess.run(['python3',str(root/'scripts/build-container-manager-trampolines.py')],check=True)
build=root/'runtime/container-manager-export';sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';guest=root/'runtime/rootfs/usr/libexec/darling'
for src,obj in [('scripts/container-manager-native-loader.c','loader.o'),('runtime/container-manager-export/trampolines.S','trampolines.o')]:
 subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-c',str(root/src),'-o',str(build/obj)],check=True)
helper='runtime/container-manager-export/libraries/libDarlingContainerManager.dylib';(root/helper).parent.mkdir(parents=True,exist_ok=True)
helper_pending=root/(helper+'.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(guest),'-lSystem','-install_name','/usr/lib/libDarlingContainerManager.dylib',str(build/'loader.o'),str(build/'trampolines.o'),'-o',str(helper_pending)],check=True)
payload,changes=api['add']((root/base).read_bytes(),'/usr/lib/libDarlingContainerManager.dylib',names)
output='runtime/container-manager-export/libraries/libSystem.B.dylib';(root/output).parent.mkdir(parents=True,exist_ok=True)
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);helper_pending.replace(root/helper);pending=root/(output+'.pending');pending.write_bytes(payload);pending.replace(root/output)
report=dict(helper=helper,helper_sha256=digest(helper),source='scripts/container-manager-native-loader.c',source_sha256=digest('scripts/container-manager-native-loader.c'),trampolines='runtime/container-manager-export/trampolines.S',trampolines_sha256=digest('runtime/container-manager-export/trampolines.S'),installed=False,runtime_execution_verified=False,base=base,base_sha256=digest(base),library=output,library_sha256=digest(output),original=original,original_sha256=digest(original),provider=provider,provider_sha256=digest(provider),client=client,client_sha256=digest(client),reconstruction_sha256=digest('runtime/rebuilt-containermanager-native/reconstruction.json'),export_changes=changes,
 scope='Only the 17 container APIs actually imported by the current original LaunchServices image are explicitly reexported through register-preserving tail-call stubs to the unchanged original Intel provider after system initialization. No container records, query results, service responses or error codes are fabricated.',full_xcode_build_ready=False,signing_ready=False)
(root/'artifacts/container-manager-export-stage.json').write_text(json.dumps(report,indent=2)+'\n');print('Exposed',len(names),'original ContainerManager entries')
