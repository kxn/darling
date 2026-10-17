#!/usr/bin/env python3
"""Run the unchanged original CoreServices daemon and observe real volume APIs."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,plistlib,runpy,subprocess,time
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('--trace',action='store_true');parser.add_argument('--paired-dirhelper',action='store_true');parser.add_argument('--source-directories',action='store_true');parser.add_argument('--tag',default='');parser.add_argument('--sandbox-resources',action='store_true');parser.add_argument('--policy-vm',action='store_true');parser.add_argument('--unrestricted-diagnostic',action='store_true');parser.add_argument('--trace-after-session',action='store_true');parser.add_argument('--fsevents-device',action='store_true');parser.add_argument('--repeat',type=int,default=1);args=parser.parse_args()
assert 1<=args.repeat<=5
if args.unrestricted_diagnostic or args.fsevents_device:args.sandbox_resources=True
if args.policy_vm:args.sandbox_resources=True
if args.sandbox_resources:args.source_directories=True
assert not args.tag or all(c.isalnum() or c=='-' for c in args.tag)
m=runpy.run_path(str(root/('scripts/fsevents-device-runtime-profile.py' if args.fsevents_device else 'scripts/coreservices-unrestricted-diagnostic-profile.py' if args.unrestricted_diagnostic else 'scripts/sandbox-policy-vm-server-profile.py' if args.policy_vm else 'scripts/sandbox-compiler-resources-profile.py' if args.sandbox_resources else 'scripts/coreservices-directories-profile.py' if args.source_directories else 'scripts/commoncrypto-original-profile.py')));p=m['profile'](diagnostic=args.unrestricted_diagnostic) if args.fsevents_device else m['profile']()
build=root/'runtime/fileidtree-service';build.mkdir(exist_ok=True);guest='/Volumes/SystemRoot/workspace/';stem='fileidtree-service-'+('fsevents-device-' if args.fsevents_device else '')+('unrestricted-diagnostic-' if args.unrestricted_diagnostic else '')+('policy-vm-' if args.policy_vm else '')+('sandbox-resources-' if args.sandbox_resources else '')+('source-dirs-' if args.source_directories else '')+('dirhelper-' if args.paired_dirhelper else '')+('trace' if args.trace else 'probe')+('-'+args.tag if args.tag else '')
env={a.split('=',1)[0]:a.split('=',1)[1] for a in p['command'] if a.startswith(('DYLD_FRAMEWORK_PATH=','DYLD_LIBRARY_PATH=','OBJC_DISABLE_TAGGED_POINTERS='))}
selections=[('coreservicesd','System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/CarbonCore.framework/Versions/A/Support/coreservicesd','com.apple.coreservicesd.plist'),('cfprefsd','usr/sbin/cfprefsd','com.apple.cfprefsd.xpc.daemon.plist')]
if args.paired_dirhelper:selections.append(('dirhelper','usr/libexec/dirhelper','com.apple.bsd.dirhelper.plist'))
jobs=[];digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
for name,relative,plist in selections:
    source='runtime/recovery/macOS Base System/'+relative;dest=build/name;dest.write_bytes((root/source).read_bytes());dest.chmod(0o755)
    originalplist='runtime/recovery/macOS Base System/System/Library/LaunchDaemons/'+plist
    job=plistlib.loads((root/originalplist).read_bytes())
    job['ProgramArguments'][0]=guest+str(dest.relative_to(root));job['EnvironmentVariables']={**job.get('EnvironmentVariables',{}),**env}
    if args.trace and name=='coreservicesd':job['EnvironmentVariables']['DYLD_INSERT_LIBRARIES']=guest+'runtime/launch-debug-gate/libDarlingLaunchDebugGate.dylib'
    job['StandardOutPath']=job['StandardErrorPath']=guest+'logs/'+stem+'-'+name+'.log'
    path=build/(stem+'-'+name+'.plist');path.write_bytes(plistlib.dumps(job));path.chmod(0o644);(root/('logs/'+stem+'-'+name+'.log')).write_text('')
    jobs.append(dict(name=name,source=source,source_sha256=digest(source),selected=str(dest.relative_to(root)),selected_sha256=digest(str(dest.relative_to(root))),original_plist=originalplist,original_plist_sha256=digest(originalplist),path=str(path.relative_to(root)),sha256=digest(str(path.relative_to(root))),job=job,binary_modified=False))
script=build/(stem+'.sh')
script.write_text('#!/bin/bash\nset -ex\n'+'\n'.join('launchctl remove '+j['job']['Label']+' || true' for j in jobs)+'\n'+'\n'.join('launchctl load '+guest+j['path'] for j in reversed(jobs))+"\ntrap '"+'; '.join('launchctl remove '+j['job']['Label']+' >/dev/null 2>&1' for j in jobs)+"' EXIT\n"+'\n'.join('launchctl list '+j['job']['Label'] for j in jobs)+'\nset +e\nstatus=0\n'+('\n'.join(guest+'runtime/fileidtree-root/test\nsample_status=$?\nif [ "$sample_status" -ne 0 ]; then status=$sample_status; fi\nsleep 2' for _ in range(args.repeat)))+'\n'+ '\n'.join('launchctl list '+j['job']['Label'] for j in jobs)+'\nprintf "FILEIDTREE_SERVICE_PROBE_STATUS %s\\n" "$status"\nexit "$status"\n')
command=p['command'][:-2]+['/bin/bash',guest+str(script.relative_to(root))];command[3]='60'
log='logs/'+stem+'.log'
with (root/log).open('w') as output:
    process=subprocess.Popen(command,env=m['environment'](p),stdout=output,stderr=subprocess.STDOUT)
    if args.trace:
        out=root/('logs/'+stem+'-coreservicesd.log');deadline=time.monotonic()+40
        while 'DARLING_LAUNCH_DEBUG_READY' not in out.read_text():
            if process.poll() is not None:raise RuntimeError('Service probe exited before trace gate')
            if time.monotonic()>deadline:raise RuntimeError('Trace gate timeout')
            time.sleep(.05)
        exe=guest+'runtime/fileidtree-service/coreservicesd';pids=[]
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit():continue
            try:argv=(entry/'cmdline').read_bytes().split(b'\0')
            except OSError:continue
            if argv[0]==exe.encode():pids.append(int(entry.name))
        assert len(pids)==1,pids
        pid=pids[0];maps=Path(f'/proc/{pid}/maps').read_text();(root/('logs/'+stem+'.maps.log')).write_text(maps)
        base=int(next(x for x in maps.splitlines() if '/CarbonCore.framework/' in x and x.split()[2]=='00000000').split('-')[0],16)
        assert digest('runtime/rebuilt-carboncore-native/CarbonCore')=='4ccae193c819a25b4578fbff9d84d918ff19c097a727a5f6e4f6b44d8bfc1f2c','Diagnostic addresses require the verified native CarbonCore image'
        sandboxbase=int(next(x for x in maps.splitlines() if '/libDarlingNativeSandbox.dylib' in x and x.split()[2]=='00000000').split('-')[0],16)
        import struct
        libcpath=root/Path(p['source_runtime']['LINUXCODE_LIBDYLD']['path']).parent/'darling-root/usr/lib/system/libsystem_c.dylib'
        libcdata=libcpath.read_bytes();sliceoff=0
        if libcdata[:4]==b'\xca\xfe\xba\xbe':
            arches=[struct.unpack_from('>IIIII',libcdata,8+i*20) for i in range(struct.unpack_from('>I',libcdata,4)[0])]
            sliceoff=next(a[2] for a in arches if a[0]==0x1000007)
        local=libcdata[sliceoff:];at=32
        for _ in range(struct.unpack_from('<I',local,16)[0]):
            cmd,length=struct.unpack_from('<II',local,at)
            if cmd==0x19 and local[at+8:at+24].split(b'\0')[0]==b'__TEXT':
                textvm,textsize,textoff,textbytes=struct.unpack_from('<QQQQ',local,at+24);break
            at+=length
        segment=next(x for x in maps.splitlines() if '/libsystem_c.dylib' in x and sliceoff+textoff<=int(x.split()[2],16)<sliceoff+textoff+textbytes)
        libcbase=int(segment.split('-')[0],16)-(textvm+int(segment.split()[2],16)-sliceoff-textoff)
        code="""set pagination off
set confirm off
python
import gdb
base=BASE_ADDRESS
class Point(gdb.Breakpoint):
 def __init__(self,addr,label,imagebase=base):
  self.label=label
  super().__init__('*'+hex(imagebase+addr),internal=False)
 def stop(self):
  extra=''
  if self.label in ['cache_mkdir_entry','cache_realpath_entry','temp_mkdir_entry','temp_realpath_entry','fsevents_open_entry']:
   try:extra=gdb.parse_and_eval('(char*)$rdi').string()
   except Exception as e:extra=str(e)
  if self.label=='libc_assert':
   try:extra='function='+gdb.parse_and_eval('(char*)$rdi').string()+' file='+gdb.parse_and_eval('(char*)$rsi').string()+' line='+str(int(gdb.parse_and_eval('$rdx')))+' expr='+gdb.parse_and_eval('(char*)$rcx').string()
   except Exception as e:extra=str(e)
  if self.label in ['sandbox_profile_failure','carbon_abort','libc_abort_report']:
   try:extra=gdb.parse_and_eval('(char*)*(unsigned long*)$rdi').string()
   except Exception as e:extra=str(e)
  print('CORESERVICES_TRACE',self.label,extra,'rax='+hex(int(gdb.parse_and_eval('$rax'))),'rdi='+hex(int(gdb.parse_and_eval('$rdi'))),flush=True)
  return self.label in ['carbon_abort','libc_abort','libc_abort_report','libc_assert'] or (self.label=='system_session_created' and DIAGNOSTIC_DETACH)
for addr,label in [(0x816ce,'server_main'),(0x81536,'sandbox_entry'),(0x8156f,'directory_suffix_return'),(0x8158d,'user_temp_confstr_return'),(0x815e9,'user_cache_confstr_return'),(0x81596,'temp_mkdir_entry'),(0x815c0,'temp_realpath_entry'),(0x815f2,'cache_mkdir_entry'),(0x81603,'cache_mkdir_return'),(0x8161c,'cache_realpath_entry'),(0x81623,'cache_realpath_return'),(0xe0f91,'failure_cold_3'),(0x81674,'sandbox_init_return'),(0x81742,'bootstrap_checkin_return'),(0x817ee,'system_session_created'),(0xe0f3a,'directory_suffix_failure'),(0xe0f71,'sandbox_profile_failure'),(0xe106d,'bootstrap_failure')]:Point(addr,label)
for addr,label in [(0x17b8,'native_sandbox_params_return'),(0x1914,'native_sandbox_compile_return'),(0x1935,'native_sandbox_apply_return')]:Point(addr,label,SANDBOX_BASE_ADDRESS)
if TRACE_AFTER_SESSION:
 for addr,label in [(0x4b122,'fsevents_open_entry'),(0x4b127,'fsevents_open_return'),(0x4b157,'fsevents_clone_entry'),(0x4b15c,'fsevents_clone_return'),(0x4b45b,'fmod_watching_return'),(0x1f9dc,'disk_arbitration_session_return'),(0x81cd1,'disk_arbitration_schedule_return')]:Point(addr,label)
 Point(0xe6f10,'carbon_abort')
 for addr,label in [(0xf12c0,'libc_abort'),(0xf1590,'libc_abort_report'),(0xef9a0,'libc_assert')]:Point(addr,label,LIBC_BASE_ADDRESS)
end
printf "CORESERVICES_BREAKPOINTS_READY\\n"
continue
python
if gdb.selected_inferior().pid:
 gdb.execute('info registers')
 gdb.execute('thread apply all bt')
 inferior=gdb.selected_inferior()
 open(STOP_MAPS_PATH,'w').write(open('/proc/'+str(inferior.pid)+'/maps').read())
 for thread in inferior.threads():
  thread.switch();print('THREAD',thread.ptid)
  print('PC',hex(int(gdb.parse_and_eval('$rip'))))
  try:
   sp=int(gdb.parse_and_eval('$rsp'));print('FRAME -1',hex(sp),hex(int.from_bytes(bytes(inferior.read_memory(sp,8)),'little')))
   fp=int(gdb.parse_and_eval('$rbp'))
   for index in range(64):
    data=bytes(inferior.read_memory(fp,16));nextfp=int.from_bytes(data[:8],'little');address=int.from_bytes(data[8:],'little')
    print('FRAME',index,hex(fp),hex(address))
    if nextfp<=fp or nextfp-fp>16777216:break
    fp=nextfp
  except Exception as e:print('FRAME_ERROR',str(e))
end
""".replace('DIAGNOSTIC_DETACH',repr(args.unrestricted_diagnostic and not args.trace_after_session)).replace('TRACE_AFTER_SESSION',repr(args.trace_after_session)).replace('LIBC_BASE_ADDRESS',hex(libcbase)).replace('STOP_MAPS_PATH',repr(str(root/('logs/'+stem+'.maps.log')))).replace('SANDBOX_BASE_ADDRESS',hex(sandboxbase)).replace('BASE_ADDRESS',hex(base))
        gdbscript=build/(stem+'.gdb');gdbscript.write_text(code);trace=root/('logs/'+stem+'.gdb.log')
        with trace.open('w') as debugout:
            debugger=subprocess.Popen(['gdb','-q','-nx','-batch','-p',str(pid),'-x',str(gdbscript)],stdout=debugout,stderr=subprocess.STDOUT)
            limit=time.monotonic()+10
            while 'CORESERVICES_BREAKPOINTS_READY' not in trace.read_text():
                if debugger.poll() is not None:raise RuntimeError('Debugger setup failed')
                if time.monotonic()>limit:raise RuntimeError('Debugger setup timed out')
                time.sleep(.05)
            with (root/'runtime/coretypes-debug-release').open('w') as fifo:fifo.write('x\n')
            try:debugger.wait(timeout=25 if args.unrestricted_diagnostic else 45)
            except subprocess.TimeoutExpired:
                debugger.send_signal(__import__('signal').SIGINT)
                debugger.wait(timeout=10)
    status=process.wait(timeout=70)
text=(root/log).read_text()
record=dict(client_samples=args.repeat,checked_at=datetime.now(timezone.utc).isoformat(),command=command,exit_status=status,jobs=jobs,log=log,log_sha256=digest(log),service_logs={str((root/('logs/'+stem+'-'+j['name']+'.log')).relative_to(root)):digest('logs/'+stem+'-'+j['name']+'.log') for j in jobs},script=str(script.relative_to(root)),script_sha256=digest(str(script.relative_to(root))),complete=False,native_sandbox_compiler=p.get('native_sandbox_compiler'),original_sandbox_resources=p.get('original_sandbox_resources'),source_coreservices_directories=p.get('source_coreservices_directories'),source_sandbox_policy_vm=p.get('source_sandbox_policy_vm'),source_unrestricted_sandbox=p.get('source_unrestricted_sandbox'),source_fsevents_device=p.get('source_fsevents_device'),diagnostic_policy=p.get('coreservices_diagnostic_policy'))
if args.trace:record.update(trace_script=str(gdbscript.relative_to(root)),trace_script_sha256=digest(str(gdbscript.relative_to(root))),maps='logs/'+stem+'.maps.log',maps_sha256=digest('logs/'+stem+'.maps.log'),trace='logs/'+stem+'.gdb.log',trace_sha256=digest('logs/'+stem+'.gdb.log'),debugger_exit_status=debugger.returncode)
(root/('artifacts/'+stem+'.json')).write_text(json.dumps(record,indent=2)+'\n');print(status,text)
