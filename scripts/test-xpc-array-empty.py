#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
build=root/'runtime/xpc-collections-source/tests';build.mkdir(exist_ok=True);obj=build/'array.o';binary=build/'array'
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-fblocks','-O2','-c','fixtures/hello/xpc-array-empty.c','-o',str(obj)],cwd=root,check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','14','14','-syslibroot',str(sdk),'-lSystem',str(obj),'-o',str(binary)],cwd=root,check=True)
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest();checks=[]
for name,script in [('old-control','log-pack'),('source','mdns-native')]:
    m=runpy.run_path(str(root/('scripts/'+script+'-profile.py')));p=m['profile'](include_system_resources=False) if name=='source' else m['profile']()
    command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))];log='logs/xpc-array-empty-'+name+'.log'
    with (root/log).open('w') as stream:result=subprocess.run(command,cwd=root,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
    text=(root/log).read_text();print(name,result.returncode,text[-2500:],flush=True)
    verified=(result.returncode!=0 and 'Symbol not found: _xpc_array_create_empty' in text) if name=='old-control' else (result.returncode==0 and 'SOURCE_XPC_EMPTY_ARRAY_REAL_MUTATION_GROWTH_RETAIN_AND_APPLY_OK' in text)
    checks.append(dict(name=name,command=command,source_runtime=p['source_runtime'],exit_status=result.returncode,log=log,log_sha256=digest(log),verified=verified))
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'source':'fixtures/hello/xpc-array-empty.c','source_sha256':digest('fixtures/hello/xpc-array-empty.c'),'binary':str(binary.relative_to(root)),'binary_sha256':digest(str(binary.relative_to(root))),'runtime_execution_verified':all(c['verified'] for c in checks),'full_xcode_build_ready':False}
(root/'artifacts/xpc-array-empty-test.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if record['runtime_execution_verified'] else 1)
