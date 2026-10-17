#!/usr/bin/env python3
"""Replay the existing pack and observer fixtures with the new source provider."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
m=runpy.run_path(str(root/'scripts/log-compose-runtime-profile.py'));p=m['profile']()
folder=root/'runtime/log-compose-tests';folder.mkdir(exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
original='fixtures/hello/log-pack.m';generated=folder/'existing-pack.m'
text=(root/original).read_text();assert text.count('/runtime/libtrace-pack-source/libraries/libTrace.dylib')==1
generated.write_text(text.replace('/runtime/libtrace-pack-source/libraries/libTrace.dylib','/runtime/log-compose-runtime/libraries/libTrace.dylib'))
checks=[]
for name,source,marker in [('pack',str(generated.relative_to(root)),'SOURCE_LOG_PACK_NATIVE_LEAF_ABI_AND_ACTUAL_DELIVERY_OK'),
                           ('hooks','fixtures/hello/log-hooks.m','SOURCE_LOG_HOOK_REAL_SERIALIZED_EVENTS_LEVELS_OWNERSHIP_REENTRANCY_FAULT_AND_CONCURRENCY_OK')]:
    obj=folder/(name+'.o');binary=folder/name
    subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-I'+str(root/'vendor/darling/src/external/libtrace/include'),
                    '-I'+str(root/'runtime/libtrace-pack-source/tests'),'-DEXPECTED_LIBTRACE_PATH="/runtime/log-compose-runtime/libraries/"',
                    '-O2','-fblocks','-c',str(root/source),'-o',str(obj)],check=True)
    subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-framework','Foundation','-lobjc','-lSystem',str(obj),'-o',str(binary)],check=True)
    command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))]
    result=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True);output=result.stdout+result.stderr
    log='logs/log-compose-'+name+'-regression.log';(root/log).write_text(output)
    match=re.search(marker+r' checks=(\d+)',output)
    checks.append(dict(name=name,command=command,exit_status=result.returncode,source=source,source_sha256=digest(source),
                       binary=str(binary.relative_to(root)),binary_sha256=digest(binary),log=log,log_sha256=digest(log),
                       checks=int(match[1]) if match else 0,verified=result.returncode==0 and match is not None))
    print(name,result.returncode,output[-1200:],flush=True)
    if not checks[-1]['verified']:break
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),checks=checks,original_pack_source=original,original_pack_source_sha256=digest(original),
            pack_test_only_change='Expected provider pathname',source_log_compose=p['source_log_compose'],
            runtime_execution_verified=len(checks)==2 and all(c['verified'] for c in checks),full_xcode_build_ready=False)
(root/'artifacts/log-compose-regressions.json').write_text(json.dumps(report,indent=2)+'\n');assert report['runtime_execution_verified']
