#!/usr/bin/env python3
"""Stage the tested Darling source component alongside its unchanged backend.

This is an incremental component build, not a full Darling rebuild. No original
runtime framework is replaced; only the separate Foundation experiment uses it.
"""
from pathlib import Path
import hashlib,json,subprocess
from datetime import datetime,timezone
root=Path(__file__).resolve().parent.parent
config=json.loads((root/'config/ca-render-server.json').read_text())
report_path=root/'artifacts/ca-render-server.json'
report=json.loads(report_path.read_text())
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=root/'vendor/darling/src/external/cocotron/QuartzCore/CARenderServer.m'
component=root/'runtime/ca-render-server/libDarlingCARenderServer.dylib'
obj=root/'runtime/ca-render-server/CARenderServer.o'
if not report['selected_api_execution_verified'] or digest(source)!=report['source_sha256'] or digest(component)!=report['library_sha256'] or digest(obj)!=report['object_sha256']:
    raise ValueError('Current source component lacks matching execution proof')
backend=root/config['backend']
if digest(backend)!=config['backend_sha256']:raise ValueError('Changed original QuartzCore backend')
stage=root/'runtime/foundation-native-library-stage'
copy=stage/'libDarlingQuartzCoreBackend.dylib';temporary=copy.with_name(copy.name+'.pending')
temporary.write_bytes(backend.read_bytes())
subprocess.run(['python3',str(root/'scripts/macho-set-id.py'),str(temporary),'/usr/lib/libDarlingQuartzCoreBackend.dylib'],check=True)
temporary.replace(copy)
guest=root/'runtime/rootfs/usr/libexec/darling'
framework_root=root/'runtime/foundation-native-framework-stage/QuartzCore.framework'
framework=framework_root/'Versions/A/QuartzCore'
framework.parent.mkdir(parents=True,exist_ok=True)
temporary=framework.with_name(framework.name+'.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11',
    '-syslibroot',str(guest),'-L',str(guest/'usr/lib'),'-lSystem',
    '-F',str(guest/'System/Library/Frameworks'),'-framework','CoreFoundation',
    '-install_name',config['provider'],'-compatibility_version','1.2.0','-current_version','1.11.0',
    '-reexport_library',str(copy),str(obj),'-o',str(temporary)],check=True)
temporary.replace(framework)
for link,target in [(framework_root/'Versions/Current','A'),(framework_root/'QuartzCore','Versions/Current/QuartzCore')]:
    if link.exists() or link.is_symlink():link.unlink()
    link.symlink_to(target)
if digest(backend)!=config['backend_sha256']:raise ValueError('Original backend was modified')
report.update(staged_at=datetime.now(timezone.utc).isoformat(),
    stage_framework=str(framework.relative_to(root)),stage_framework_sha256=digest(framework),
    stage_backend=str(copy.relative_to(root)),stage_backend_sha256=digest(copy),
    original_backend_unchanged=True,full_darling_rebuild=False,
    integration='Source component linked with reexport of existing Darling QuartzCore under a distinct backend identity; isolated experimental stage only')
report_path.write_text(json.dumps(report,indent=2)+'\n')
print('Staged tested Darling QuartzCore source component; original runtime unchanged')
