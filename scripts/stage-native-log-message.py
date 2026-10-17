#!/usr/bin/env python3
"""Forward the exact XCTest import to the previously restored native formatter."""
from pathlib import Path
import fcntl,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
digest=lambda s:hashlib.sha256((root/s).read_bytes()).hexdigest()
base='runtime/log-enablement/libraries/libSystem.B.dylib'
old=json.loads((root/'artifacts/log-enablement-stage.json').read_text());assert digest(base)==old['library_sha256']
provider='runtime/state/prefix/usr/lib/libDarlingMetrics.dylib'
reconstruction='runtime/rebuilt-native-trace/reconstruction.json';r=json.loads((root/reconstruction).read_text());assert digest(provider)==r['staged_image_sha256']
pin=json.loads((root/'config/cache-image-pins.json').read_text())['native-trace'];assert r['original_image_sha256']==pin['sha256']
source='scripts/native-log-message-loader.c';build=root/'runtime/native-log-message';libraries=build/'libraries';libraries.mkdir(parents=True,exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';guest=root/'runtime/rootfs/usr/libexec/darling'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-c',str(root/source),'-o',str(build/'loader.o')],check=True)
helper='runtime/native-log-message/libraries/libDarlingLogMessage.dylib';pending=root/(helper+'.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(guest),'-lSystem','-install_name','/usr/lib/libDarlingLogMessage.dylib',str(build/'loader.o'),'-o',str(pending)],check=True)
payload,changes=runpy.run_path(str(root/'scripts/macho-named-reexport.py'))['add']((root/base).read_bytes(),'/usr/lib/libDarlingLogMessage.dylib',['_os_log_copy_message_string'])
output='runtime/native-log-message/libraries/libSystem.B.dylib'
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);pending.replace(root/helper);temporary=root/(output+'.pending');temporary.write_bytes(payload);temporary.replace(root/output)
report=dict(base=base,base_sha256=digest(base),library=output,library_sha256=digest(output),helper=helper,helper_sha256=digest(helper),source=source,source_sha256=digest(source),provider=provider,provider_sha256=digest(provider),reconstruction=reconstruction,reconstruction_sha256=digest(reconstruction),original_provider=pin,export_changes=changes,installed=False,runtime_execution_verified=False,
 scope='Exact original message formatter with unchanged message pointers and owned return. Original legacy log/activity class registration remains excluded in the existing metrics reconstruction; original metric classes retained. Lazy loading does not claim all unused native trace imports are supported.')
(root/'artifacts/native-log-message-stage.json').write_text(json.dumps(report,indent=2)+'\n');print('Staged deferred call to the original native log message formatter')
