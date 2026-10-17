#!/usr/bin/env python3
"""Capture real syscall return bytes and the Foundation abort frame chain."""
from pathlib import Path
import os, runpy, subprocess, time
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/metadata-kernel-profile.py'));p=m['profile']()
c=p['command'][:-2]+['/Volumes/SystemRoot/workspace/artifacts/coretypes-resource-values','--wait'];c[3]='180'
c.insert(c.index('/usr/bin/env')+1,'DARLING_OS_LOG_STDERR=1')
log=root/'logs/metadata-kernel-foundation-debug.log'
with log.open('w') as output:
    process=subprocess.Popen(c,cwd=root,env=m['environment'](p),stdout=output,stderr=subprocess.STDOUT,text=True)
    deadline=time.monotonic()+60
    while 'CORETYPES_METADATA_READY' not in log.read_text():
        if process.poll() is not None:raise RuntimeError('Fixture exited before gate')
        if time.monotonic()>deadline:raise RuntimeError('Gate timeout')
        time.sleep(.1)
    pids=[]
    for item in Path('/proc').iterdir():
        if not item.name.isdigit():continue
        try:argv=(item/'cmdline').read_bytes().split(b'\0')
        except OSError:continue
        if argv[0]==b'/Volumes/SystemRoot/workspace/artifacts/coretypes-resource-values':pids.append(int(item.name))
    assert len(pids)==1,pids
    pid=pids[0];maps=Path(f'/proc/{pid}/maps').read_text();(root/'logs/metadata-kernel-foundation-maps.log').write_text(maps)
    base=int(next(x for x in maps.splitlines() if 'libsystem_kernel.dylib' in x and x.split()[2]=='00000000').split('-')[0],16)
    symbols={line.split()[-1]:int(line.split()[0],16) for line in subprocess.check_output(['llvm-nm-19','-n',str(root/'runtime/metadata-kernel-source/libsystem_kernel.dylib')],text=True).splitlines() if len(line.split())==3}
    script='''set pagination off
set confirm off
python
import gdb
class Entry(gdb.Breakpoint):
 def stop(self):
  ptr=int(gdb.parse_and_eval('$rdx'));buffer=int(gdb.parse_and_eval('$rcx'));size=int(gdb.parse_and_eval('$r8'))
  print('METADATA_AT options='+hex(int(gdb.parse_and_eval('$r9')))+' size='+str(size))
  gdb.execute('x/6wx '+hex(ptr));gdb.execute('x/s $rsi')
  address=int.from_bytes(gdb.selected_inferior().read_memory(int(gdb.parse_and_eval('$rsp')),8),'little')
  # Entry-only tracing avoids the host GDB 16 breakpoint deletion defect.
  return False
Entry('*ENTRY')
class Bulk(gdb.Breakpoint):
 def stop(self):
  print('METADATA_BULK fd='+str(int(gdb.parse_and_eval('$rdi')))+' size='+str(int(gdb.parse_and_eval('$rcx')))+' options='+hex(int(gdb.parse_and_eval('$r8'))))
  gdb.execute('x/6wx $rsi')
  return False
Bulk('*BULKADDRESS')
class Dents(gdb.Breakpoint):
 def stop(self):
  print('METADATA_DENTS fd='+str(int(gdb.parse_and_eval('$rdi')))+' bytes='+str(int(gdb.parse_and_eval('$rdx'))))
  return False
Dents('*DENTSADDRESS')
Dents('*DENTSATTRADDRESS')
end
printf "METADATA_BREAKPOINTS_READY\\n"
continue
python
print('METADATA_STOP')
fp=int(gdb.parse_and_eval('$rbp')) if gdb.selected_inferior().pid else 0
for i in range(40 if fp else 0):
 try:
  data=bytes(gdb.selected_inferior().read_memory(fp,16));nextfp=int.from_bytes(data[:8],'little');ret=int.from_bytes(data[8:],'little');print('FRAME',hex(fp),hex(ret))
  if nextfp<=fp or nextfp-fp>0x100000:break
  fp=nextfp
 except Exception as e:print(e);break
end
python
if gdb.selected_inferior().pid:
 gdb.execute("info registers");gdb.execute("x/80gx $rsp")
end
'''.replace('ENTRY',hex(base+symbols['_sys_getattrlistat'])).replace('BULKADDRESS',hex(base+symbols['_sys_getattrlistbulk'])).replace('DENTSADDRESS',hex(base+symbols['_sys_getdirentries64'])).replace('DENTSATTRADDRESS',hex(base+symbols['_sys_getdirentriesattr']))
    scriptpath=root/'runtime/metadata-kernel-foundation.gdb';scriptpath.write_text(script)
    gdblog=root/'logs/metadata-kernel-foundation-gdb.log'
    with gdblog.open('w') as outputg:
        debugger=subprocess.Popen(['nsenter','--target',str(pid),'--user','--preserve-credentials','gdb','-q','-nx','-batch','-p',str(pid),'-x',str(scriptpath)],stdout=outputg,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+30
        while 'METADATA_BREAKPOINTS_READY' not in gdblog.read_text():
            if debugger.poll() is not None:raise RuntimeError('Debugger exited before attaching')
            if time.monotonic()>deadline:raise RuntimeError('Debugger readiness timeout')
            time.sleep(.1)
        with (root/'runtime/coretypes-debug-release').open('w') as gate:gate.write('x\n')
        debugger.wait(timeout=90)
    print('fixture status',process.wait(timeout=30),'debugger',debugger.returncode)
print(log.read_text()[-4000:])
print(gdblog.read_text()[-9000:])
