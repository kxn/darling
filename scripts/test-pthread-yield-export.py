#!/usr/bin/env python3
"""Verify the actual export and observe real Linux scheduling syscalls with ptrace."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,re,subprocess
root=Path(__file__).resolve().parent.parent
read=lambda p:json.loads((root/p).read_text());digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
stage=read('artifacts/pthread-yield-export-stage.json');probe=read('artifacts/security-policy-source-xcode-probe.json')
assert digest(stage['staged_library'])==stage['staged_library_sha256']
assert digest(stage['provider'])==stage['provider_sha256'] and digest(stage['base'])==stage['base_sha256']
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
guestroot=root/'runtime/rootfs/usr/libexec/darling'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-c',
    str(root/'fixtures/hello/pthread-yield-export.c'),'-o',str(root/'artifacts/pthread-yield-export.o')],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(guestroot),'-lSystem',
    str(root/'artifacts/pthread-yield-export.o'),'-o',str(root/'artifacts/pthread-yield-export')],check=True)
environment=os.environ.copy()
for name,item in probe['source_runtime'].items():
    assert digest(item['path'])==item['sha256'];environment[name]=str(root/item['path'])
guest='/Volumes/SystemRoot/workspace/';base=list(probe['command'][:probe['command'].index('/usr/bin/xcodebuild')])
tail=[guest+'artifacts/pthread-yield-export',guest+stage['provider']]
negative='logs/pthread-yield-export-baseline.log'
with (root/negative).open('w') as stream:
    subprocess.run(base+tail+['--missing'],cwd=root,env=environment,stdout=stream,stderr=subprocess.STDOUT,check=True)
assert 'BASELINE_LIBSYSTEM_HAS_NO_PTHREAD_YIELD_NP_EXPORT_OK\n' in (root/negative).read_text()
key='DYLD_LIBRARY_PATH=';index=next(i for i,v in enumerate(base) if v.startswith(key))
base[index]=key+guest+'runtime/pthread-yield-export/libraries:'+base[index].split('=',1)[1]
trace='logs/pthread-yield-export-linux-syscalls.log';log='logs/pthread-yield-export-execute.log'
strace=root/'runtime/tools/strace/usr/bin/strace';assert strace.is_file()
command=[str(strace),'-f','-s','120','-e','trace=sched_yield,write','-o',str(root/trace),*base,*tail]
with (root/log).open('w') as stream:
    result=subprocess.run(command,cwd=root,env=environment,stdout=stream,stderr=subprocess.STDOUT)
print('yield execution',result.returncode,flush=True)
assert result.returncode==0,(root/log).read_text()[-6000:]
assert 'PTHREAD_YIELD_REAL_256_MAIN_AND_1024_EIGHT_THREAD_CALLS_OK\n' in (root/log).read_text()
lines=(root/trace).read_text().splitlines();start=next(i for i,line in enumerate(lines) if 'write(1, "YIELD_BEGIN' in line)
end=next(i for i,line in enumerate(lines[start+1:],start+1) if 'write(1, "YIELD_END' in line)
pid=lines[start].split()[0];pending={};completed=[]
for i,line in enumerate(lines):
    begin=re.match(r'(\d+)\s+sched_yield\(',line)
    resume=re.match(r'(\d+)\s+<\.\.\. sched_yield resumed>',line)
    if begin:
        owner=begin[1];assert owner not in pending
        if '<unfinished ...>' in line:pending[owner]=i;continue
        first=i
    elif resume:
        owner=resume[1];assert owner in pending;first=pending.pop(owner)
    else:continue
    result=re.search(r'\)\s+=\s+(-?\d+)',line);assert result,line
    completed.append((owner,first,i,int(result[1])))
calls=[entry for entry in completed if entry[0]==pid and start<entry[1]<=entry[2]<end]
assert len(calls)==256 and all(entry[3]==0 for entry in calls),(pid,len(calls))
all_yields=len(completed);assert all_yields>=1280,all_yields
kernel='vendor/darling/src/external/xnu/darling/src/libsystem_kernel/emulation/src/'
backend_files=[kernel+'xnu_syscall/mach/impl/mach_traps.c',kernel+'linux_premigration/ext/sched_yield.c',
    'vendor/darling/src/external/libpthread/src/pthread.c','scripts/foundation-libc-compat.c']
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),runtime_execution_verified=True,stage=stage,
    selected_runtime=probe['source_runtime'],command=command,
    baseline_export_absence_verified=True,real_existing_helper_resolved=True,
    exact_main_thread_Linux_sched_yield_syscalls_between_markers=256,
    minimum_total_Linux_sched_yield_syscalls=all_yields,all_main_thread_yields_succeeded=True,
    test_source_sha256=digest('fixtures/hello/pthread-yield-export.c'),test_binary_sha256=digest('artifacts/pthread-yield-export'),
    test_driver_sha256=digest('scripts/test-pthread-yield-export.py'),strace_sha256=digest(strace),
    backend_source_files={p:digest(p) for p in backend_files},logs={p:digest(p) for p in [negative,log,trace]},
    full_xcode_build_ready=False,signing_ready=False)
(root/'artifacts/pthread-yield-export-execution.json').write_text(json.dumps(record,indent=2)+'\n')
print('Verified named export and 256 exact successful main-thread Linux sched_yield syscalls plus eight-thread calls')
