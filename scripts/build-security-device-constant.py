#!/usr/bin/env python3
"""Compile the native identifier value; do not emulate an attestation service."""
from pathlib import Path
import fcntl,hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent;digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
reference_name='artifacts/security-anonymous-attestation-constant-reference.json';reference=json.loads((root/reference_name).read_text());assert digest(reference['provider'])==reference['provider_sha256']
name=reference['symbol'].removeprefix('_');source='vendor/darling/src/external/security/OSX/sec/Security/SecItemConstants.c'
lines=re.findall(r'^SEC_CONST_DECL \('+name+r', "([^"]+)"\);$',(root/source).read_text(),re.M);assert lines==[reference['value']]
build=root/'runtime/security-device-constants';build.mkdir(exist_ok=True);component=build/'constant.c';component.write_text('#define __CONSTANT_CFSTRINGS__ 1\n#include <CoreFoundation/CFString.h>\nconst CFStringRef '+name+' = CFSTR("'+reference['value']+'");\n')
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';obj=build/'constant.o'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-c',str(component),'-o',str(obj)],check=True)
library=build/'libraries/libDarlingSecurityDeviceConstants.dylib';library.parent.mkdir(exist_ok=True)
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-framework','CoreFoundation','-lSystem','-install_name','/usr/lib/'+library.name,str(obj),'-o',str(library)],check=True)
base='runtime/security-cloud-rpc-stage/frameworks/Security.framework/Versions/A/Security';old=json.loads((root/'artifacts/security-cloud-rpc-stage.json').read_text());assert digest(base)==old['library_sha256']
payload,changes=runpy.run_path(str(root/'scripts/macho-named-reexport.py'))['add']((root/base).read_bytes(),'/usr/lib/'+library.name,[reference['symbol']])
framework=build/'frameworks/Security.framework';output=framework/'Versions/A/Security';output.parent.mkdir(parents=True,exist_ok=True)
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);output.write_bytes(payload)
 for path,destination in [(framework/'Versions/Current','A'),(framework/'Security','Versions/Current/Security')]:
  if not path.is_symlink():path.symlink_to(destination)
record=dict(source=source,source_sha256=digest(source),component=str(component.relative_to(root)),component_sha256=digest(str(component.relative_to(root))),library=str(library.relative_to(root)),library_sha256=digest(str(library.relative_to(root))),framework=str(output.relative_to(root)),framework_sha256=digest(str(output.relative_to(root))),base=base,base_sha256=digest(base),reference=reference_name,reference_sha256=digest(reference_name),value=reference['value'],export_changes=changes,full_Security_source_build=False,attestation_service_implemented=False,runtime_execution_verified=False)
(root/'artifacts/security-device-constant-build.json').write_text(json.dumps(record,indent=2)+'\n');print('Compiled actual Security identifier',reference['value'],'and retained real Security backend')
