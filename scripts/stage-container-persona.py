#!/usr/bin/env python3
"""Recover the actual C-string constants consumed by original XCTHarness."""
from pathlib import Path
from datetime import datetime,timezone
import fcntl,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
digest=lambda s:hashlib.sha256((root/s).read_bytes()).hexdigest()
m=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h','REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
old=json.loads((root/'artifacts/container-manager-export-stage.json').read_text());assert digest(old['original'])==old['original_sha256']
values={}
for name in ['CONTAINER_PERSONA_PRIMARY','CONTAINER_PERSONA_CURRENT']:
 a=m['resolve']('/usr/lib/system/libsystem_containermanager.dylib','_'+name);text=m['read'](m['pointer'](a),128).split(b'\0')[0].decode('ascii');values[name]=dict(address=hex(a),string_address=hex(m['pointer'](a)),value=text)
source='scripts/container-persona-constants.c';text=(root/source).read_text()
for name,v in values.items():assert name+'="'+v['value']+'";' in text
build=root/'runtime/container-persona';libraries=build/'libraries';libraries.mkdir(parents=True,exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';guest=root/'runtime/rootfs/usr/libexec/darling'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-c',str(root/source),'-o',str(build/'constants.o')],check=True)
helper='runtime/container-persona/libraries/libDarlingContainerPersona.dylib';pending=root/(helper+'.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(guest),'-lSystem','-install_name','/usr/lib/libDarlingContainerPersona.dylib',str(build/'constants.o'),'-o',str(pending)],check=True)
base='runtime/log-hooks/libraries/libSystem.B.dylib';stage=json.loads((root/'artifacts/log-hooks-stage.json').read_text());assert digest(base)==stage['library_sha256']
payload,changes=runpy.run_path(str(root/'scripts/macho-named-reexport.py'))['add']((root/base).read_bytes(),'/usr/lib/libDarlingContainerPersona.dylib',['_'+n for n in values])
output='runtime/container-persona/libraries/libSystem.B.dylib'
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);pending.replace(root/helper);temporary=root/(output+'.pending');temporary.write_bytes(payload);temporary.replace(root/output)
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),base=base,base_sha256=digest(base),library=output,library_sha256=digest(output),helper=helper,helper_sha256=digest(helper),source=source,source_sha256=digest(source),original=old['original'],original_sha256=digest(old['original']),provider=old['provider'],provider_sha256=digest(old['provider']),values=values,export_changes=changes,installed=False,runtime_execution_verified=False,
 scope='Exact C-string values and pointer-variable ABI. String storage addresses differ; no persona records, query success or account authorization are fabricated.')
(root/'artifacts/container-persona-stage.json').write_text(json.dumps(record,indent=2)+'\n');print('Staged two verified original persona C-string values')
