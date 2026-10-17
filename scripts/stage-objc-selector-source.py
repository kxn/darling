#!/usr/bin/env python3
"""Use the source selector API while retaining the existing enumeration adapter."""
from pathlib import Path
from datetime import datetime,timezone
import fcntl,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent;digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
report='artifacts/objc-selector-source-build.json';build=json.loads((root/report).read_text());assert build['full_objc_source_build'] and build['complete_source_files']==43 and build['source_export_count']==771
assert digest(build['library'])==build['library_sha256']
for n,sha in build['source_files'].items():assert digest('vendor/darling/src/external/objc4/runtime/'+n)==sha
folder=root/'runtime/objc-selector-source/libraries';folder.mkdir(parents=True,exist_ok=True);source='scripts/objc-class-enumeration.c';sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';guest=root/'runtime/rootfs/usr/libexec/darling'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-fblocks','-c',str(root/source),'-o',str(folder/'enumeration.o')],check=True)
base='runtime/objc-selector-source/libraries/enumeration-base.dylib';subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(guest),'-L',str(guest/'usr/lib'),'-lobjc','-lSystem','-headerpad','0x1000','-install_name','/usr/lib/libDarlingObjCEnumeration.dylib',str(folder/'enumeration.o'),'-o',str(root/base)],check=True)
payload,changes=runpy.run_path(str(root/'scripts/macho-named-reexport.py'))['add']((root/base).read_bytes(),'/usr/lib/libobjc.A.dylib',['_sel_lookUpByName'])
helper='runtime/objc-selector-source/libraries/libDarlingObjCEnumeration.dylib'
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);pending=root/(helper+'.pending');pending.write_bytes(payload);pending.replace(root/helper)
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),build_report=report,build_report_sha256=digest(report),library=build['library'],library_sha256=digest(build['library']),helper=helper,helper_sha256=digest(helper),enumeration_source=source,enumeration_source_sha256=digest(source),base=base,base_sha256=digest(base),export_changes=changes,old_guard_source='scripts/objc-selector-lookup.c',old_guard_source_sha256=digest('scripts/objc-selector-lookup.c'),installed=False,runtime_execution_verified=False,scope='The private composition uses the actual new source sel_lookUpByName under its own selLock and builtin selector lookup. The old guarded adapter is unchanged and not linked into this private helper. Existing class-enumeration behavior remains source-backed by the same runtime layout/public snapshots; no guard is weakened or private old selector offsets reused.')
(root/'artifacts/objc-selector-source-stage.json').write_text(json.dumps(record,indent=2)+'\n');print('Staged real source selector lookup and named helper reexport')
