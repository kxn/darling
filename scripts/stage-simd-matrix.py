#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import fcntl,hashlib,json,runpy,struct,subprocess
root=Path(__file__).resolve().parent.parent;digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
m=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h','REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
provider='/usr/lib/system/libsystem_m.dylib';address=m['resolve'](provider,'_matrix_identity_float3x3');assert address
original=m['read'](address,48);assert struct.unpack('<12f',original)==(1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.)
build=root/'runtime/simd-matrix-source';build.mkdir(parents=True,exist_ok=True);(build/'libraries').mkdir(exist_ok=True)
source='vendor/darling/src/libm/Source/simd_constants.c';sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-c',str(root/source),'-o',str(build/'constants.o')],check=True)
helper='runtime/simd-matrix-source/libraries/libDarlingSIMDMatrix.dylib';pending=root/(helper+'.pending');subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-lSystem','-install_name','/usr/lib/libDarlingSIMDMatrix.dylib',str(build/'constants.o'),'-o',str(pending)],check=True)
a=int(next(x.split()[0] for x in subprocess.check_output(['llvm-nm-19',str(pending)],text=True).splitlines() if x.endswith(' _matrix_identity_float3x3')),16);data=pending.read_bytes();count=struct.unpack_from('<I',data,16)[0];at=32;value=None
for _ in range(count):
 cmd,n=struct.unpack_from('<II',data,at)
 if cmd==0x19:
  start,size,off,length=struct.unpack_from('<QQQQ',data,at+24)
  if start<=a<a+48<=start+length:value=data[off+a-start:off+a-start+48]
 at+=n
assert value==original and a%16==0
base='runtime/runnable-archs-source/libraries/libSystem.B.dylib';stage=json.loads((root/'artifacts/runnable-archs-source-stage.json').read_text());assert digest(base)==stage['library_sha256']
payload,changes=runpy.run_path(str(root/'scripts/macho-named-reexport.py'))['add']((root/base).read_bytes(),'/usr/lib/libDarlingSIMDMatrix.dylib',['_matrix_identity_float3x3']);output='runtime/simd-matrix-source/libraries/libSystem.B.dylib'
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);pending.replace(root/helper);temp=root/(output+'.pending');temp.write_bytes(payload);temp.replace(root/output)
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),base=base,base_sha256=digest(base),source=source,source_sha256=digest(source),helper=helper,helper_sha256=digest(helper),library=output,library_sha256=digest(output),provider=provider,provider_sha256=digest('runtime/fullsystem-libraries'+provider),original_address=hex(address),original_bytes=original.hex(),source_bytes_equal_original=True,source_alignment=16,export_changes=changes,installed=False,runtime_execution_verified=False,full_libm_source_build=False)
(root/'artifacts/simd-matrix-source-stage.json').write_text(json.dumps(record,indent=2)+'\n');print('Staged source SIMD identity with exact native 48-byte layout')
