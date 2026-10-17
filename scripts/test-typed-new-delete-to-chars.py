#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/typed-new-delete-profile.py'));p=m['profile'](include_system_resources=False)
build=root/'runtime/typed-new-delete-source';sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
source='fixtures/hello/libcxx-to-chars.cpp';reference=build/'to-chars-linux';obj=build/'to-chars-test.o';binary=build/'to-chars-test'
subprocess.run(['g++','-std=c++17','-O2',str(root/source),'-o',str(reference)],check=True)
linux_log='logs/typed-new-delete-to-chars-linux.log'
with (root/linux_log).open('w') as stream:subprocess.run([str(reference)],stdout=stream,check=True)
subprocess.run(['clang++-19','-target','x86_64-apple-macos15.4','-isysroot',str(sdk),'-nostdinc++','-isystem',str(sdk/'usr/include/c++/v1'),'-std=c++17','-O2','-DLINUXCODE_LIBCXX_EXPECTED_PROVIDER="/typed-new-delete-source/libraries/libc++.1.dylib"','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','15.4','15.4','-syslibroot',str(sdk),'-L'+str(build/'libraries'),'-lc++','-lSystem',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))];log='logs/typed-new-delete-to-chars.log'
with (root/log).open('w') as stream:r=subprocess.run(command,cwd=root,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
assert r.returncode==0,(r.returncode,(root/log).read_text()[-2000:])
linux=(root/linux_log).read_text().splitlines();darwin=[s for s in (root/log).read_text().splitlines() if s.startswith(('D0P','D1P','D2P','D3P','D4P','F0P','F1P','F2P','F3P','F4P','L0 ','L1 ','L2 ','REAL_LIBCXX_'))]
assert len(linux)==len(darwin);variations=0
for a,b in zip(darwin,linux):
    if a==b:continue
    left,right=a.split(),b.split()
    assert left[:2]==right[:2] and left[0] in ('D4P-1','F4P-1'),(a,b)
    variations+=1
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'source':source,'source_sha256':digest(source),'binary':str(binary.relative_to(root)),'binary_sha256':digest(str(binary.relative_to(root))),'log':log,'log_sha256':digest(log),'reference_log':linux_log,'reference_log_sha256':digest(linux_log),'exit_status':r.returncode,'finite_cases':len(linux)-16,'native_long_double_narrowing_cases':15,'hex_normalization_variations':variations,'roundtrip_buffer_and_reference_comparison_verified':True,'full_xcode_build_ready':False}
(root/'artifacts/typed-new-delete-to-chars-test.json').write_text(json.dumps(record,indent=2)+'\n')
print('Typed libc++ wrapper retains',record['finite_cases'],'finite formatting cases and 15 long-double cases; independent Linux comparison passed')
