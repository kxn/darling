#!/usr/bin/env python3
"""Inspect real CarbonCore local-universe initialization, optionally with gdb."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,subprocess,time
root=Path(__file__).resolve().parent.parent
assert hashlib.sha256((root/'runtime/rebuilt-carboncore-native/CarbonCore').read_bytes()).hexdigest()=='4ccae193c819a25b4578fbff9d84d918ff19c097a727a5f6e4f6b44d8bfc1f2c','Private diagnostic offsets require the verified CarbonCore image'
parser=argparse.ArgumentParser();parser.add_argument('--trace',action='store_true');args=parser.parse_args()
m=runpy.run_path(str(root/'scripts/commoncrypto-original-profile.py'));p=m['profile']()
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';build=root/'runtime/fileidtree-root';build.mkdir(exist_ok=True);source='fixtures/hello/fileidtree-root.m';obj=build/'test.o';binary=build/'test'
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-Wno-deprecated-declarations','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','14','14','-syslibroot',str(sdk),'-lSystem','-lobjc','-framework','Foundation',str(obj),'-o',str(binary)],check=True)
exe='/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root));command=p['command'][:-2]+[exe]+(['--trace'] if args.trace else [])
stem='fileidtree-root-'+('trace' if args.trace else 'probe');log='logs/'+stem+'.log'
with (root/log).open('w') as stream:
    process=subprocess.Popen(command,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
    if args.trace:
        deadline=time.monotonic()+15
        while 'FILEIDTREE_TRACE_READY' not in (root/log).read_text():
            if process.poll() is not None:raise RuntimeError('Probe exited before trace gate')
            if time.monotonic()>deadline:raise RuntimeError('Trace gate timeout')
            time.sleep(.03)
        pids=[]
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit():continue
            try:argv=(entry/'cmdline').read_bytes().split(b'\0')
            except OSError:continue
            if argv[0]==exe.encode():pids.append(int(entry.name))
        assert len(pids)==1,pids
        pid=pids[0];maps=Path(f'/proc/{pid}/maps').read_text();(root/('logs/'+stem+'.maps.log')).write_text(maps)
        base=int(next(x for x in maps.splitlines() if '/CarbonCore.framework/' in x and x.split()[2]=='00000000').split('-')[0],16)
        code='''set pagination off
set confirm off
python
import gdb
base=BASE_ADDRESS
seq=0
def reg(n):return int(gdb.parse_and_eval('$'+n))
def mem(n,size):return bytes(gdb.selected_inferior().read_memory(n,size))
class Point(gdb.Breakpoint):
 def __init__(self,addr,label):
  self.label=label
  super().__init__('*'+hex(base+addr),internal=False)
 def stop(self):
  global seq
  seq+=1
  try:
   extra=''
   if self.label=='once_block':extra='server_callbacks='+str(mem(reg('rdi')+40,1)[0])+' universe='+hex(int.from_bytes(mem(reg('rdi')+32,8),'little'))
   if self.label=='device_filter':extra='device_0x4c='+mem(reg('rbx')+76,4).hex()+' caps_0x98='+mem(reg('rbx')+152,4).hex()+' path_0xb0='+mem(reg('rbx')+176,4).hex()
   if self.label=='mount_entry':extra='mount='+repr(mem(reg('rsi')+88,1024).split(b'\\0')[0])
   print('FILEIDTREE_TRACE',seq,self.label,'rax='+hex(reg('rax')),'rdi='+hex(reg('rdi')),'rsi='+hex(reg('rsi')),extra,flush=True)
  except Exception as e:print('FILEIDTREE_TRACE_ERROR',self.label,str(e),flush=True)
  return False
for addr,label in [(0x4671c,'once_block'),(0x46746,'server_runloop'),(0x4675b,'basesystem_return'),(0x4677c,'root_statfs_return'),(0x467d5,'root_mount_return'),(0x4684c,'preboot_mount_return'),(0x197b0,'mount_entry'),(0x19a59,'mount_failed'),(0x10b36,'first_device_root'),(0x10b61,'first_device_return'),(0x109d3,'device_filter'),(0x109e2,'network_disable_return'),(0x109f3,'network_filter_passed'),(0x10a06,'options_filter_passed'),(0x10a84,'path_reference_missing')]:Point(addr,label)
end
printf "FILEIDTREE_BREAKPOINTS_READY\\n"
continue
'''.replace('BASE_ADDRESS',hex(base))
        gdbscript=build/'trace.gdb';gdbscript.write_text(code)
        with (root/('logs/'+stem+'.gdb.log')).open('w') as out:
            debugger=subprocess.run(['gdb','-q','-nx','-batch','-p',str(pid),'-x',str(gdbscript)],stdout=out,stderr=subprocess.STDOUT,timeout=30)
    status=process.wait(timeout=70)
text=(root/log).read_text();digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),command=command,exit_status=status,log=log,log_sha256=digest(log),source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),probe_returned='NATIVE_VOLUMES_PROBE_RETURNED' in text,filecoordination_service_verified=False)
if args.trace:
    record.update(debugger_exit_status=debugger.returncode,trace='logs/'+stem+'.gdb.log',trace_sha256=digest('logs/'+stem+'.gdb.log'),maps='logs/'+stem+'.maps.log',maps_sha256=digest('logs/'+stem+'.maps.log'))
(root/('artifacts/'+stem+'.json')).write_text(json.dumps(record,indent=2)+'\n');print(status,text)
