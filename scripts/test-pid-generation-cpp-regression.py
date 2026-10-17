#!/usr/bin/env python3
"""Run actual expected/allocator/formatting regressions in the new full runtime."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/pid-generation-source-profile.py'));p=m['profile'](False)
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
build=root/'runtime/expected-access-source/regression';build.mkdir(exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
flags=['clang++-19','-target','x86_64-apple-macos15.4','-isysroot',str(sdk),'-nostdinc++','-isystem',str(sdk/'usr/include/c++/v1'),'-std=c++17','-O2','-fexceptions','-c']
library=root/'runtime/expected-access-source/libraries'
sources=['fixtures/hello/typed-new-delete-source.cpp','fixtures/hello/typed-new-delete-replacements.cpp','fixtures/hello/libcxx-to-chars.cpp']
provider='/expected-access-source/libraries/libc++.1.dylib'
executables=[]
for mode in ['default','replacements','formatting']:
    binary=build/mode;obj=build/(mode+'.o')
    source=sources[2] if mode=='formatting' else sources[0]
    macro='LINUXCODE_LIBCXX_EXPECTED_PROVIDER' if mode=='formatting' else 'LINUXCODE_TYPED_NEW_EXPECTED_PROVIDER'
    target_version='15.4' if mode=='formatting' else '11'
    mode_flags=[s.replace('x86_64-apple-macos15.4','x86_64-apple-macos'+target_version) for s in flags]
    subprocess.run([*mode_flags,'-D'+macro+'="'+provider+'"',*(['-DTEST_REPLACEMENTS'] if mode=='replacements' else []),str(root/source),'-o',str(obj)],check=True)
    objects=[str(obj)]
    if mode=='replacements':
        extra=build/'replacement-functions.o';subprocess.run([*mode_flags,str(root/sources[1]),'-o',str(extra)],check=True);objects.append(str(extra))
    subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos',target_version,target_version,'-syslibroot',str(sdk),'-L'+str(library),'-lc++','-lSystem',*objects,'-o',str(binary)],check=True)
    executables.append((mode,binary))
expected=json.loads((root/'artifacts/expected-access-source-test.json').read_text())
for key in ['binary','fixture']:assert digest(expected[key])==expected[key+'_sha256']
executables.insert(0,('expected',root/expected['binary']))
rows=[]
for mode,binary in executables:
    command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))]
    if mode=='expected':command=[s.replace('DYLD_LIBRARY_PATH=','DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/expected-access-source/fixture-libraries:',1) if s.startswith('DYLD_LIBRARY_PATH=') else s for s in command]
    log='logs/pid-generation-cpp-'+mode+'.log'
    with (root/log).open('w') as stream:r=subprocess.run(command,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
    text=(root/log).read_text();print(mode,r.returncode,text[-600:],flush=True)
    rows.append(dict(mode=mode,command=command,exit_status=r.returncode,binary=str(binary.relative_to(root)),binary_sha256=digest(str(binary.relative_to(root))),log=log,log_sha256=digest(log)))
    assert r.returncode==0,(mode,text[-2000:])
reference=build/'formatting-linux';reference_log='logs/pid-generation-cpp-formatting-linux.log'
subprocess.run(['g++','-std=c++17','-O2',str(root/sources[2]),'-o',str(reference)],check=True)
with (root/reference_log).open('w') as stream:subprocess.run([str(reference)],stdout=stream,check=True)
linux=(root/reference_log).read_text().splitlines();darwin=[s for s in (root/rows[-1]['log']).read_text().splitlines() if s.startswith(('D0P','D1P','D2P','D3P','D4P','F0P','F1P','F2P','F3P','F4P','L0 ','L1 ','L2 ','REAL_LIBCXX_'))]
assert len(linux)==len(darwin);variations=0
for a,b in zip(darwin,linux):
    if a==b:continue
    left,right=a.split(),b.split();assert left[:2]==right[:2] and left[0] in ('D4P-1','F4P-1'),(a,b);variations+=1
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'sources':{n:digest(n) for n in sources},'checks':rows,'reference_log':reference_log,'reference_log_sha256':digest(reference_log),'finite_cases':len(linux)-16,'native_long_double_narrowing_cases':15,'hex_normalization_variations':variations,'roundtrip_buffer_and_reference_comparison_verified':True,'full_xcode_build_ready':False}
(root/'artifacts/pid-generation-cpp-regression.json').write_text(json.dumps(record,indent=2)+'\n')
print('Expected RTTI/cross-DSO exceptions, typed allocation/replacement, and all finite formatting checks passed in the new source kernel/server runtime')
