#!/usr/bin/env python3
from pathlib import Path
import fcntl,hashlib,json,runpy,shutil
root=Path(__file__).resolve().parent.parent
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
build=json.loads((root/'artifacts/security-cloud-rpc-build.json').read_text())
for name,sha in {**build['sources'],**build['generated_headers']}.items():assert digest(name)==sha
assert digest(build['library'])==build['library_sha256']
base='runtime/mdns-native/frameworks/Security.framework/Versions/A/Security'
assert digest(base)==build['native_security_sha256']
payload,changes=runpy.run_path(str(root/'scripts/macho-named-reexport.py'))['add']((root/base).read_bytes(),'/usr/lib/libDarlingSecurityCloudRPC.dylib',build['public_RPCs']+build.get('public_value_class_exports',[]))
stage=root/'runtime/security-cloud-rpc-stage';destination=stage/'frameworks/Security.framework/Versions/A/Security';destination.parent.mkdir(parents=True,exist_ok=True)
provider=stage/'libraries/libDarlingSecurityCloudRPC.dylib';provider.parent.mkdir(exist_ok=True)
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    pending=provider.with_suffix('.pending');shutil.copyfile(root/build['library'],pending);pending.replace(provider)
    pending=destination.with_suffix('.pending');pending.write_bytes(payload);pending.replace(destination)
    framework=stage/'frameworks/Security.framework'
    for target,value in [(framework/'Versions/Current','A'),(framework/'Security','Versions/Current/Security')]:
        if not target.is_symlink():target.symlink_to(value)
report={'base':base,'base_sha256':digest(base),'library':str(destination.relative_to(root)),'library_sha256':digest(str(destination.relative_to(root))),'provider':str(provider.relative_to(root)),'provider_sha256':digest(str(provider.relative_to(root))),'build':build,'export_changes':changes,'default_launcher_changed':False,'runtime_execution_verified':False,'full_xcode_build_ready':False}
(root/'artifacts/security-cloud-rpc-stage.json').write_text(json.dumps(report,indent=2)+'\n')
print('Staged actual RPC and result-class exports from real source client; native Security code retained')
