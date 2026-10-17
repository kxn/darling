#!/usr/bin/env python3
"""Capture actual statfs paths/returns from original lsd before CoreTypes registration."""
from pathlib import Path
import os,runpy,re,subprocess,time
root=Path(__file__).resolve().parent.parent
prefix='native-lsd-debug-gate-container-manager-metadata-kernel-sysdir-paired-dirhelper-sandbox-container-datavault-user-local-dir-source-libtrace'
subprocess.run(['python3',str(root/'scripts/build-launch-debug-gate.py')],check=True)
fifo=root/'runtime/coretypes-debug-release'
if not fifo.exists():os.mkfifo(fifo,0o600)
log=root/('logs/'+prefix+'-daemon.log')
if log.exists():log.write_text('')
with (root/'logs/native-lsd-statfs-debug-driver.log').open('w') as driver:
 process=subprocess.Popen(['python3',str(root/'scripts/probe-native-lsd.py'),'--source-libtrace','--user-local-dir-export','--rootless-datavault-export','--sandbox-container','--with-dirhelper','--native-sysdir','--metadata-kernel','--native-container-manager','--debug-gate'],cwd=root,stdout=driver,stderr=subprocess.STDOUT)
 deadline=time.monotonic()+60
 while not log.exists() or 'DARLING_LAUNCH_DEBUG_READY' not in log.read_text():
  if process.poll() is not None:raise RuntimeError('lsd probe exited before diagnostic gate')
  if time.monotonic()>deadline:raise RuntimeError('Gate readiness timeout')
  time.sleep(.1)
 pids=[]
 for entry in Path('/proc').iterdir():
  if not entry.name.isdigit():continue
  try:argv=(entry/'cmdline').read_bytes().split(b'\0')
  except OSError:continue
  if argv[0]==b'/Volumes/SystemRoot/workspace/runtime/native-lsd/lsd':pids.append(int(entry.name))
 assert len(pids)==1,pids
 pid=pids[0];maps=Path(f'/proc/{pid}/maps').read_text();(root/'logs/native-lsd-statfs-live-maps.log').write_text(maps)
 base=int(next(x for x in maps.splitlines() if 'libsystem_kernel.dylib' in x and x.split()[2]=='00000000').split('-')[0],16)
 kernel=root/'runtime/metadata-kernel-source/libsystem_kernel.dylib'
 syms={l.split()[-1]:int(l.split()[0],16) for l in subprocess.check_output(['llvm-nm-19','-n',str(kernel)],text=True).splitlines() if len(l.split())==3}
 dis=subprocess.check_output(['llvm-objdump-19','--disassemble-symbols=_sys_statfs64',str(kernel)],text=True)
 returns=[int(a,16) for a in re.findall(r'^\s*([0-9a-f]+):[^\n]*\bretq\b',dis,re.M)];assert returns
 script='''set pagination off
set confirm off
python
import gdb
pending={}
def key():return (gdb.selected_thread().ptid,int(gdb.parse_and_eval('$rsp')))
class Entry(gdb.Breakpoint):
 def stop(self):
  try:path=gdb.parse_and_eval('(char*)$rdi').string()
  except Exception as e:path=str(e)
  pending[key()]=path
  return False
class Returned(gdb.Breakpoint):
 def stop(self):
  path=pending.pop(key(),None);result=int(gdb.parse_and_eval('(long long)$rax'))
  if result or (path and 'CoreTypes' in path):print('LSD_STATFS_RESULT',result,repr(path),flush=True)
  return False
Entry('*ENTRYADDRESS')
'''.replace('ENTRYADDRESS',hex(base+syms['_sys_statfs64']))
 script+='\n'.join("Returned('*"+hex(base+a)+"')" for a in returns)
 script+='''
end
printf "LSD_STATFS_BREAKPOINTS_READY\\n"
continue
python
print('LSD_STATFS_STOP')
if gdb.selected_inferior().pid:
 gdb.execute('info registers');gdb.execute('x/12i $rip')
 fp=int(gdb.parse_and_eval('$rbp'))
 for i in range(35):
  try:
   v=bytes(gdb.selected_inferior().read_memory(fp,16));new=int.from_bytes(v[:8],'little');ret=int.from_bytes(v[8:],'little');print('FRAME',hex(fp),hex(ret))
   if new<=fp or new-fp>0x100000:break
   fp=new
  except Exception:break
end
'''
 sp=root/'runtime/native-lsd-statfs.gdb';sp.write_text(script)
 out=root/'logs/native-lsd-statfs-gdb.log'
 with out.open('w') as output:
  debugger=subprocess.Popen(['nsenter','--target',str(pid),'--user','--preserve-credentials','gdb','-q','-nx','-batch','-p',str(pid),'-x',str(sp)],stdout=output,stderr=subprocess.STDOUT)
  deadline=time.monotonic()+30
  while 'LSD_STATFS_BREAKPOINTS_READY' not in out.read_text():
   if debugger.poll() is not None:raise RuntimeError('Debugger failed before readiness')
   if time.monotonic()>deadline:raise RuntimeError('Debugger readiness timeout')
   time.sleep(.1)
  with fifo.open('w') as gate:gate.write('x\n')
  debugger.wait(timeout=140)
 print('debugger status',debugger.returncode,'probe status',process.wait(timeout=30))
print(out.read_text()[-6500:])
