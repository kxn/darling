#!/usr/bin/env python3
"""Compare the pack ABI with original Intel leaf code, then send real log packs."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,struct,subprocess
root=Path(__file__).resolve().parent.parent
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
m=runpy.run_path(str(root/'scripts/log-pack-profile.py'));p=m['profile']()
original='runtime/fullsystem-libraries/usr/lib/system/libsystem_trace.dylib'
data=(root/original).read_bytes();commands=struct.unpack_from('<I',data,16)[0];offset=32;segments=[]
for _ in range(commands):
    cmd,length=struct.unpack_from('<II',data,offset)
    if cmd==0x19:segments.append(struct.unpack_from('<QQQQ',data,offset+24))
    offset+=length
symbols={line.split()[-1]:int(line.split()[0],16) for line in subprocess.check_output(['llvm-nm-19',str(root/original)],text=True).splitlines() if len(line.split())==3 and line.split()[1]!='U'}
test_dir=root/'runtime/libtrace-pack-source/tests';test_dir.mkdir(exist_ok=True)
oracle={};declarations=[]
for name,symbol,length in [('native_pack_size','__os_log_pack_size',5),('native_pack_fill','__os_log_pack_fill',62)]:
    address=symbols[symbol];segment=next(s for s in segments if s[0]<=address and address+length<=s[0]+s[3])
    code=data[segment[2]+address-segment[0]:segment[2]+address-segment[0]+length];assert code[-1]==0xc3
    oracle[name]=dict(symbol=symbol,address=hex(address),length=length,sha256=hashlib.sha256(code).hexdigest())
    declarations.append('static const unsigned char '+name+'[]={'+','.join(hex(b) for b in code)+'};')
header=test_dir/'native-pack-oracle.h';header.write_text('\n'.join(declarations)+'\n')
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
obj=test_dir/'log-pack.o';binary=test_dir/'log-pack'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-I'+str(root/'vendor/darling/src/external/libtrace/include'),'-I'+str(test_dir),'-fblocks','-O2','-c','fixtures/hello/log-pack.m','-o',str(obj)],cwd=root,check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-framework','Foundation','-lobjc','-lSystem',str(obj),'-o',str(binary)],cwd=root,check=True)
hook_obj=test_dir/'log-hooks.o';hook_binary=test_dir/'log-hooks'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-I'+str(root/'vendor/darling/src/external/libtrace/include'),'-DEXPECTED_LIBTRACE_PATH="/runtime/libtrace-pack-source/"','-fblocks','-O2','-c','fixtures/hello/log-hooks.m','-o',str(hook_obj)],cwd=root,check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-framework','Foundation','-lobjc','-lSystem',str(hook_obj),'-o',str(hook_binary)],cwd=root,check=True)
checks=[]
for name,target,marker in [('pack',binary,'SOURCE_LOG_PACK_NATIVE_LEAF_ABI_AND_ACTUAL_DELIVERY_OK'),('hooks',hook_binary,'LOG_HOOK')]:
    command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(target.relative_to(root))]
    log='logs/log-pack-'+name+'-test.log'
    with (root/log).open('w') as stream:result=subprocess.run(command,cwd=root,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
    text=(root/log).read_text();print(name,result.returncode,text[-3500:],flush=True)
    checks.append(dict(name=name,command=command,exit_status=result.returncode,log=log,log_sha256=digest(log),verified=result.returncode==0 and marker in text))
    if not checks[-1]['verified']:break
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'original':original,'original_sha256':digest(original),'native_leaf_oracle':oracle,'source':'fixtures/hello/log-pack.m','source_sha256':digest('fixtures/hello/log-pack.m'),'binary':str(binary.relative_to(root)),'binary_sha256':digest(str(binary.relative_to(root))),'hook_source_sha256':digest('fixtures/hello/log-hooks.m'),'hook_binary_sha256':digest(str(hook_binary.relative_to(root))),'runtime_execution_verified':len(checks)==2 and all(c['verified'] for c in checks),'full_unified_log_service_verified':False,'full_xcode_build_ready':False}
(root/'artifacts/log-pack-test.json').write_text(json.dumps(record,indent=2)+'\n')
raise SystemExit(0 if record['runtime_execution_verified'] else 1)
