#!/usr/bin/env python3
"""Load the unchanged original disk daemon and exercise its native SDK client."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,plistlib,re,runpy,subprocess,time,signal
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('--tag',default='initial');parser.add_argument('--without-daemon',action='store_true');parser.add_argument('--debug',action='store_true');parser.add_argument('--trace',action='store_true');parser.add_argument('--iokitd-runtime',choices=['baseline','source','matching','mounts']);parser.add_argument('--source-iokitd-build');parser.add_argument('--power-client',action='store_true');parser.add_argument('--mount-client',action='store_true');parser.add_argument('--store-client',action='store_true');parser.add_argument('--log-compose',action='store_true');parser.add_argument('--configd',action='store_true');parser.add_argument('--iokitd',action='store_true');parser.add_argument('--trace-target',choices=['diskarbitrationd','configd','iokitd'],default='diskarbitrationd');parser.add_argument('--coreservices',action='store_true');parser.add_argument('--unrestricted-diagnostic',action='store_true');parser.add_argument('--volume-probe',action='store_true');args=parser.parse_args()
assert not args.unrestricted_diagnostic or (args.coreservices and args.iokitd_runtime=='mounts')
assert args.trace_target!='configd' or args.configd
if args.source_iokitd_build:args.iokitd=True
assert not (args.trace and args.without_daemon and args.trace_target=='diskarbitrationd')
assert args.tag and all(c.isalnum() or c=='-' for c in args.tag)
m=runpy.run_path(str(root/('scripts/mount-volumes-diagnostic-profile.py' if args.unrestricted_diagnostic else 'scripts/mount-flags-runtime-profile.py' if args.iokitd_runtime=='mounts' else 'scripts/iokitd-matching-runtime-profile.py' if args.iokitd_runtime=='matching' else 'scripts/iokitd-power-runtime-profile.py' if args.iokitd_runtime else 'scripts/log-compose-runtime-profile.py' if args.log_compose else 'scripts/fsevents-device-runtime-profile.py')));p=m['profile'](baseline=args.iokitd_runtime=='baseline') if args.iokitd_runtime in ['source','baseline'] else m['profile']()
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
build=root/'runtime/diskarbitration-service';build.mkdir(exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
source='fixtures/hello/'+('mount-notification.c' if args.mount_client else 'iokit-power-probe.c' if args.power_client else 'systemconfiguration-store.c' if args.store_client else 'diskarbitration-service.c');obj=build/('mount-client.o' if args.mount_client else 'power-client.o' if args.power_client else 'store-client.o' if args.store_client else 'client.o');binary=build/('mount-client' if args.mount_client else 'power-client' if args.power_client else 'store-client' if args.store_client else 'client')
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-O0','-Wno-deprecated-declarations','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','14','14','-syslibroot',str(sdk),'-lSystem','-framework','CoreFoundation','-framework','DiskArbitration',*(['-undefined','dynamic_lookup'] if args.mount_client else []),*(['-framework','IOKit'] if args.power_client else ['-framework','SystemConfiguration'] if args.store_client else []),str(obj),'-o',str(binary)],check=True)
stem='diskarbitration-service-'+('no-daemon-' if args.without_daemon else '')+args.tag;guest='/Volumes/SystemRoot/workspace/'
env={a.split('=',1)[0]:a.split('=',1)[1] for a in p['command'] if a.startswith(('DYLD_FRAMEWORK_PATH=','DYLD_LIBRARY_PATH=','OBJC_DISABLE_TAGGED_POINTERS='))}
original='runtime/recovery/macOS Base System/usr/libexec/diskarbitrationd'
daemon=build/'diskarbitrationd';daemon.write_bytes((root/original).read_bytes());daemon.chmod(0o755)
original_plist='runtime/recovery/macOS Base System/System/Library/LaunchDaemons/com.apple.diskarbitrationd.plist'
job=plistlib.loads((root/original_plist).read_bytes());job['Program']=guest+str(daemon.relative_to(root))
if args.debug:job['ProgramArguments']=[job['Program'],'-d']
job['EnvironmentVariables']={**job.get('EnvironmentVariables',{}),**env}
if args.trace and args.trace_target=='diskarbitrationd':job['EnvironmentVariables']['DYLD_INSERT_LIBRARIES']=guest+'runtime/launch-debug-gate/libDarlingLaunchDebugGate.dylib'
job['StandardOutPath']=job['StandardErrorPath']=guest+'logs/'+stem+'-daemon.log'
jobfile=build/(stem+'.plist');jobfile.write_bytes(plistlib.dumps(job));jobfile.chmod(0o644)
(root/('logs/'+stem+'-daemon.log')).write_text('')
companions=[]
core_companions=[('com.apple.coreservicesd','runtime/recovery/macOS Base System/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/CarbonCore.framework/Versions/A/Support/coreservicesd','runtime/recovery/macOS Base System/System/Library/LaunchDaemons/com.apple.coreservicesd.plist')] if args.coreservices else []
for label,executable,plist in ([('com.apple.configd','runtime/recovery/macOS Base System/usr/libexec/configd','runtime/recovery/macOS Base System/System/Library/LaunchDaemons/com.apple.configd.plist')] if args.configd else [])+([('org.darlinghq.iokitd','runtime/rootfs/usr/libexec/darling/usr/sbin/iokitd','runtime/rootfs/usr/libexec/darling/System/Library/LaunchDaemons/org.darlinghq.iokitd.plist')] if args.iokitd else [])+core_companions:
    name=label.split('.')[-1]
    if name=='iokitd' and args.source_iokitd_build:
        source_build=json.loads((root/args.source_iokitd_build).read_text());executable=source_build['binary'];assert digest(executable)==source_build['binary_sha256']
    target=build/(name+'-'+digest(executable)[:12] if name=='iokitd' and args.source_iokitd_build else name);target.write_bytes((root/executable).read_bytes());target.chmod(0o755)
    companion=plistlib.loads((root/plist).read_bytes());companion['ProgramArguments']=[guest+str(target.relative_to(root))]
    companion['EnvironmentVariables']={**companion.get('EnvironmentVariables',{}),**env}
    if args.trace and args.trace_target==name:companion['EnvironmentVariables']['DYLD_INSERT_LIBRARIES']=guest+'runtime/launch-debug-gate/libDarlingLaunchDebugGate.dylib'
    if args.trace and name=='iokitd':companion['EnvironmentVariables']['DARLING_OS_LOG_STDERR']='1'
    companion['StandardOutPath']=companion['StandardErrorPath']=guest+'logs/'+stem+'-'+name+'.log'
    (root/('logs/'+stem+'-'+name+'.log')).write_text('')
    selected=build/(stem+'-'+name+'.plist');selected.write_bytes(plistlib.dumps(companion));selected.chmod(0o644)
    companions.append(dict(source=executable,source_sha256=digest(executable),binary=str(target.relative_to(root)),binary_sha256=digest(target),original_plist=plist,original_plist_sha256=digest(plist),job=companion,path=str(selected.relative_to(root)),sha256=digest(selected)))

script=build/(stem+'.sh')
script.write_text('#!/bin/bash\nset -ex\nlaunchctl remove com.apple.diskarbitrationd || true\n'+
    (''.join('launchctl remove '+c['job']['Label']+' || true\nlaunchctl load '+guest+c['path']+'\n' for c in reversed(companions)))+
    ('' if args.without_daemon else 'launchctl load '+guest+str(jobfile.relative_to(root))+'\n')+
    "trap 'launchctl remove com.apple.diskarbitrationd >/dev/null 2>&1 || true; "+"; ".join("launchctl remove "+c["job"]["Label"]+" >/dev/null 2>&1 || true" for c in companions)+"' EXIT\n"+
    guest+str(binary.relative_to(root))+'\nstatus=$?\n'+(guest+'runtime/mount-volume-probe/native\n' if args.volume_probe else '')+'sleep 1\n'+''.join('launchctl list '+c['job']['Label']+' || true\n' for c in companions)+'launchctl list com.apple.diskarbitrationd || true\nexit "$status"\n')
command=p['command'][:-2]+['/bin/bash',guest+str(script.relative_to(root))];command[3]='60'
log='logs/'+stem+'.log'
with (root/log).open('w') as output:
    process=subprocess.Popen(command,env=m['environment'](p),stdout=output,stderr=subprocess.STDOUT)
    if args.trace:
        target_program=job['Program'] if args.trace_target=='diskarbitrationd' else next(c['job']['ProgramArguments'][0] for c in companions if c['job']['Label'].split('.')[-1]==args.trace_target)
        deadline=time.monotonic()+35;daemon_log=root/('logs/'+stem+('-daemon' if args.trace_target=='diskarbitrationd' else '-'+args.trace_target)+'.log')
        while 'DARLING_LAUNCH_DEBUG_READY' not in daemon_log.read_text():
            if process.poll() is not None:raise RuntimeError('Probe ended before daemon debug gate')
            if time.monotonic()>deadline:raise RuntimeError('Daemon debug gate timeout')
            time.sleep(.05)
        matches=[]
        for item in Path('/proc').iterdir():
            if not item.name.isdigit():continue
            try:argv=(item/'cmdline').read_bytes().split(b'\0')
            except OSError:continue
            if argv[0]==target_program.encode():matches.append(int(item.name))
        assert len(matches)==1,matches
        pid=matches[0];maps=Path(f'/proc/{pid}/maps').read_text();(root/('logs/'+stem+'.maps.log')).write_text(maps)
        base=int(next(row for row in maps.splitlines() if '/runtime/diskarbitration-service/'+args.trace_target in row and row.split()[2]=='00000000').split('-')[0],16)
        code="""set pagination off
set confirm off
python
import gdb
base=BASE
class Point(gdb.Breakpoint):
 def __init__(self,offset,label):
  self.label=label
  super().__init__('*'+hex(base+offset))
 def stop(self):
  extra=''
  if self.label in ['fatal_log','registry_from_path']:
   try:extra=gdb.parse_and_eval('(char*)$rsi' if self.label=='registry_from_path' else '(char*)$rdi').string()
   except Exception as e:extra=str(e)
  print('DAEMON_TRACE',self.label,'rdi='+hex(int(gdb.parse_and_eval('$rdi'))),'rax='+hex(int(gdb.parse_and_eval('$rax'))),extra,flush=True)
  return self.label=='exit'
TRACE_POINTS
end
printf "DAEMON_BREAKPOINTS_READY\\n"
continue
python
gdb.execute('info registers')
gdb.execute('thread apply all bt')
inferior=gdb.selected_inferior()
open(MAPS,'w').write(open('/proc/'+str(inferior.pid)+'/maps').read())
for thread in inferior.threads():
 thread.switch();print('THREAD',thread.ptid)
 print('PC',hex(int(gdb.parse_and_eval('$rip'))))
 try:
  sp=int(gdb.parse_and_eval('$rsp'));print('FRAME -1',hex(sp),hex(int.from_bytes(bytes(inferior.read_memory(sp,8)),'little')))
  fp=int(gdb.parse_and_eval('$rbp'))
  for index in range(50):
   data=bytes(inferior.read_memory(fp,16));n=int.from_bytes(data[:8],'little');address=int.from_bytes(data[8:],'little')
   print('FRAME',index,hex(fp),hex(address))
   if n<=fp or n-fp>16777216:break
   fp=n
 except Exception as e:print('FRAME_ERROR',str(e))
end
""".replace('TRACE_POINTS',"Point(0x1222,'main')\nPoint(0x69656,'exit')\nPoint(0x69548,'exit')" if args.trace_target=='configd' else "Point(0xda0,'main')\nPoint(0xde0,'master_checkin_return')\nPoint(0xe50,'power_checkin_return')\nPoint(0x11f0,'iokit_request')\nPoint(0x91d0,'registry_from_path')\nPoint(0xee5,'bootstrap_complete')\nPoint(0x5cc0,'io_object_constructor')" if args.trace_target=='iokitd' else "Point(0x92a2,'main')\nPoint(0x9651,'dynamic_store_create_return')\nPoint(0x9695,'system_power_return')\nPoint(0x8b11,'fatal_log')\nPoint(0x1e28a,'exit')").replace('BASE',hex(base)).replace('MAPS',repr(str(root/('logs/'+stem+'.maps.log'))))
        gdbscript=build/(stem+'.gdb');gdbscript.write_text(code);trace=root/('logs/'+stem+'.gdb.log')
        with trace.open('w') as debug:
            debugger=subprocess.Popen(['gdb','-q','-nx','-batch','-p',str(pid),'-x',str(gdbscript)],stdout=debug,stderr=subprocess.STDOUT)
            deadline=time.monotonic()+10
            while 'DAEMON_BREAKPOINTS_READY' not in trace.read_text():
                if debugger.poll() is not None:raise RuntimeError('Debugger failed before setup')
                if time.monotonic()>deadline:raise RuntimeError('Debugger setup timeout')
                time.sleep(.05)
            with (root/'runtime/coretypes-debug-release').open('w') as fifo:fifo.write('x\n')
            try:debugger.wait(timeout=30)
            except subprocess.TimeoutExpired:
                debugger.send_signal(signal.SIGINT);debugger.wait(timeout=10)
    status=process.wait(timeout=70)
text=(root/log).read_text()
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),command=command,exit_status=status,
            source_iokitd_build=args.source_iokitd_build,source_iokitd_build_sha256=digest(args.source_iokitd_build) if args.source_iokitd_build else None,without_daemon=args.without_daemon,companion_jobs=companions,companion_logs={c["job"]["StandardOutPath"].removeprefix(guest):digest(c["job"]["StandardOutPath"].removeprefix(guest)) for c in companions},source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),
            daemon_source=original,daemon_source_sha256=digest(original),daemon=str(daemon.relative_to(root)),daemon_sha256=digest(daemon),daemon_binary_modified=False,
            original_plist=original_plist,original_plist_sha256=digest(original_plist),job=job,path=str(jobfile.relative_to(root)),sha256=digest(jobfile),
            script=str(script.relative_to(root)),script_sha256=digest(script),log=log,log_sha256=digest(log),
            daemon_log='logs/'+stem+'-daemon.log',daemon_log_sha256=digest('logs/'+stem+'-daemon.log'),source_mount_flags=p.get('source_mount_flags'),mount_volumes_diagnostic=p.get('mount_volumes_diagnostic'),source_iokitd_matching=p.get('source_iokitd_matching'),source_iokitd_power=p.get('source_iokitd_power'),source_runtime=p['source_runtime'],source_fsevents_device=p['source_fsevents_device'],source_log_compose=p.get('source_log_compose'),
            native_store_functional='NATIVE_SYSTEMCONFIGURATION_REAL_CONFIGD_STORE_AND_NOTIFICATION_OK' in text,native_session_created='DA_PROBE_RETURNED session=1' in text or 'NATIVE_REAL_LINUX_MOUNT_UPDATE_UNMOUNT_NOTIFICATIONS_OK' in text,
            native_volume_description_verified=all(re.search(r'MOUNT_DA_VOLUME path='+re.escape(path)+r' disk=0x[1-9a-f][0-9a-f]* description=0x[1-9a-f][0-9a-f]*',text) for path in ['/','/Volumes/SystemRoot','/Volumes/SystemRoot/']),
            volume_probe_binary='runtime/mount-volume-probe/native' if args.volume_probe else None,volume_probe_binary_sha256=digest('runtime/mount-volume-probe/native') if args.volume_probe else None,
            full_xcode_build_ready=False)
if args.trace:report.update(trace_script=str(gdbscript.relative_to(root)),trace_script_sha256=digest(gdbscript),trace='logs/'+stem+'.gdb.log',trace_sha256=digest(trace),maps='logs/'+stem+'.maps.log',maps_sha256=digest('logs/'+stem+'.maps.log'),debugger_exit_status=debugger.returncode)
(root/('artifacts/'+stem+'.json')).write_text(json.dumps(report,indent=2)+'\n');print(status,text[-6000:]);print((root/report['daemon_log']).read_text()[-4000:])
