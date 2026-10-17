#!/usr/bin/env python3
"""Stage the tested Darling CoreGraphics component with its original backend."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess
root=Path(__file__).resolve().parent.parent
c=json.loads((root/'config/cgs-accelerator.json').read_text())
path=root/'artifacts/cgs-accelerator.json';report=json.loads(path.read_text())
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
obj=root/'runtime/cgs-accelerator/production.o'
if not report['selected_backend_ownership_execution_verified'] or digest(root/c['source'])!=report['source_sha256'] or digest(obj)!=report['object_sha256']:
    raise ValueError('Source component changed after testing')
backend=root/c['backend']
if digest(backend)!=c['backend_sha256']:raise ValueError('Changed original CoreGraphics')
copy=root/'runtime/foundation-native-library-stage/libDarlingCoreGraphicsBackend.dylib'
temporary=copy.with_name(copy.name+'.pending');temporary.write_bytes(backend.read_bytes())
subprocess.run(['python3',str(root/'scripts/macho-set-id.py'),str(temporary),'/usr/lib/libDarlingCoreGraphicsBackend.dylib'],check=True)
temporary.replace(copy)
bundle=root/'runtime/foundation-native-framework-stage/CoreGraphics.framework'
output=bundle/'Versions/A/CoreGraphics';output.parent.mkdir(parents=True,exist_ok=True)
temporary=output.with_name(output.name+'.pending');guest=root/'runtime/rootfs/usr/libexec/darling'
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11',
    '-syslibroot',str(guest),'-lSystem','-F',str(guest/'System/Library/Frameworks'),'-framework','IOKit',
    '-install_name',c['provider'],'-compatibility_version','64.0.0','-current_version','1070.22.0',
    '-reexport_library',str(copy),str(obj),'-o',str(temporary)],check=True)
temporary.replace(output)
for link,target in [(bundle/'Versions/Current','A'),(bundle/'CoreGraphics','Versions/Current/CoreGraphics')]:
    if link.exists() or link.is_symlink():link.unlink()
    link.symlink_to(target)
if digest(backend)!=c['backend_sha256']:raise ValueError('Original CoreGraphics was modified')
report.update(staged_at=datetime.now(timezone.utc).isoformat(),full_darling_rebuild=False,
    stage_framework=str(output.relative_to(root)),stage_framework_sha256=digest(output),
    stage_backend=str(copy.relative_to(root)),stage_backend_sha256=digest(copy),original_backend_unchanged=True)
path.write_text(json.dumps(report,indent=2)+'\n')
print('Staged production Darling CoreGraphics source; test backend not included')
