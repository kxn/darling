#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/expected-access-source-profile.py'));p=m['profile'](False)
parent=runpy.run_path(str(root/'scripts/sandbox-check-source-profile.py'));old=parent['profile'](False)
build=root/'runtime/expected-access-source';folder=build/'fixture-libraries';folder.mkdir(exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
flags=['clang++-19','-target','x86_64-apple-macos26','-isysroot',str(sdk),'-nostdinc++','-isystem',str(sdk/'usr/include/c++/v1'),'-std=c++23','-O2','-fexceptions','-c']
normalizer=runpy.run_path(str(root/'scripts/normalize-macho-weak-bind.py'))['normalize'];normalizations={}
for name in ['producer','source']:
    subprocess.run([*flags,str(root/('fixtures/hello/expected-access-'+name+'.cpp')),'-o',str(build/(name+'.o'))],check=True)
fixture=folder/'libExpectedFixture.dylib'
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','26','26','-no_fixup_chains','-syslibroot',str(sdk),'-L'+str(build/'libraries'),'-lc++','-lSystem','-install_name','/usr/lib/libExpectedFixture.dylib',str(build/'producer.o'),'-o',str(fixture)],check=True)
payload,normalizations['producer']=normalizer(fixture.read_bytes());fixture.write_bytes(payload)
binary=build/'test'
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','26','26','-no_fixup_chains','-syslibroot',str(sdk),'-L'+str(build/'libraries'),'-L'+str(folder),'-lExpectedFixture','-lc++','-lSystem',str(build/'source.o'),'-o',str(binary)],check=True)
payload,normalizations['consumer']=normalizer(binary.read_bytes());binary.write_bytes(payload)
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest();rows=[]
for label,profile,module in [('old-control',old,parent),('source',p,m)]:
    command=profile['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))]
    command=[s.replace('DYLD_LIBRARY_PATH=','DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/expected-access-source/fixture-libraries:',1) if s.startswith('DYLD_LIBRARY_PATH=') else s for s in command]
    log='logs/expected-access-source-'+label+'.log'
    with (root/log).open('w') as stream:r=subprocess.run(command,env=module['environment'](profile),stdout=stream,stderr=subprocess.STDOUT)
    print(label,r.returncode,(root/log).read_text()[-2500:],flush=True)
    rows.append({'profile':label,'command':command,'exit_status':r.returncode,'log':log,'log_sha256':digest(log)})
files=['fixtures/hello/expected-access-'+n for n in ['fixture.h','producer.cpp','source.cpp']]
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'sources':{n:digest(n) for n in files},'checks':rows,'binary':str(binary.relative_to(root)),'binary_sha256':digest(str(binary.relative_to(root))),'fixture':str(fixture.relative_to(root)),'fixture_sha256':digest(str(fixture.relative_to(root))),'fixture_weak_bind_normalizations':normalizations,'full_xcode_build_ready':False}
(root/'artifacts/expected-access-source-test.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if rows[0]['exit_status']!=0 and rows[1]['exit_status']==0 else 1)
