#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/typed-new-delete-profile.py'));p=m['profile'](include_system_resources=False)
old=runpy.run_path(str(root/'scripts/security-cloud-rpc-profile.py'));base=old['profile'](include_system_resources=False)
build=root/'runtime/typed-new-delete-source';sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
source='fixtures/hello/typed-new-delete-source.cpp';replacement='fixtures/hello/typed-new-delete-replacements.cpp';rows=[]
for mode in ['default','replacements']:
    obj=build/('test-'+mode+'.o');binary=build/('test-'+mode)
    flags=['clang++-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-nostdinc++','-isystem',str(sdk/'usr/include/c++/v1'),'-std=c++17','-O2','-fexceptions','-c']
    subprocess.run([*flags,*(['-DTEST_REPLACEMENTS'] if mode=='replacements' else []),str(root/source),'-o',str(obj)],check=True)
    objects=[str(obj)]
    if mode=='replacements':
        extra=build/'replacements.o';subprocess.run([*flags,str(root/replacement),'-o',str(extra)],check=True);objects.append(str(extra))
    subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-L'+str(build/'libraries'),'-lc++','-lSystem',*objects,'-o',str(binary)],check=True)
    bad={**p,'command':list(p['command'])}
    bad['command']=[arg.replace('/runtime/typed-new-delete-source/libraries:', '/runtime/typed-new-delete-source/unsorted-control:') for arg in bad['command']]
    for label,profile,module in ([('old-control',base,old),('source',p,m)] if mode=='default' else [('unsorted-control',bad,m),('source',p,m)]):
        command=profile['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))];log='logs/typed-new-delete-'+mode+'-'+label+'.log'
        with (root/log).open('w') as stream:r=subprocess.run(command,cwd=root,env=module['environment'](profile),stdout=stream,stderr=subprocess.STDOUT)
        text=(root/log).read_text();print(mode,label,r.returncode,text[-2000:],flush=True)
        rows.append({'mode':mode,'profile':label,'exit_status':r.returncode,'log':log,'log_sha256':digest(log),'binary':str(binary.relative_to(root)),'binary_sha256':digest(str(binary.relative_to(root)))})
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'sources':{n:digest(n) for n in [source,replacement]},'checks':rows,'type_partition_isolation_verified':False,'full_xcode_build_ready':False}
(root/'artifacts/typed-new-delete-test.json').write_text(json.dumps(record,indent=2)+'\n')
raise SystemExit(0 if [r['exit_status']==0 for r in rows]==[False,True,False,True] else 1)
