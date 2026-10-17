#!/usr/bin/env python3
"""Catch the actual original lsd fault in the current source logging profile."""
from pathlib import Path
import os,subprocess,time
root=Path(__file__).resolve().parent.parent
subprocess.run(['python3','scripts/build-launch-debug-gate.py'],cwd=root,check=True)
fifo=root/'runtime/coretypes-debug-release'
if not fifo.exists():os.mkfifo(fifo,0o600)
stem='native-lsd-container-persona-debug-gate';log=root/('logs/'+stem+'-daemon.log')
log.write_text('')
with (root/'logs/log-hooks-lsd-debug-driver.log').open('w') as stream:
 process=subprocess.Popen(['python3','scripts/probe-native-lsd.py','--source-libtrace','--user-local-dir-export','--rootless-datavault-export','--sandbox-container','--with-dirhelper','--native-sysdir','--metadata-kernel','--native-container-manager','--mount-path-kernel','--layer-log','--native-message','--latest-profile','container-persona','--debug-gate'],cwd=root,stdout=stream,stderr=subprocess.STDOUT)
 deadline=time.monotonic()+60
 while 'DARLING_LAUNCH_DEBUG_READY' not in log.read_text():
  if process.poll() is not None:raise RuntimeError('Probe stopped before the diagnostic gate')
  if time.monotonic()>deadline:raise RuntimeError('Readiness observation timed out; inspect the existing process')
  time.sleep(.1)
 pids=[]
 for entry in Path('/proc').iterdir():
  if not entry.name.isdigit():continue
  try:argv=(entry/'cmdline').read_bytes().split(b'\0')
  except OSError:continue
  if argv[0]==b'/Volumes/SystemRoot/workspace/runtime/native-lsd/lsd':pids.append(int(entry.name))
 assert len(pids)==1,pids
 pid=pids[0];script=root/'runtime/log-hooks-lsd.gdb';out=root/'logs/log-hooks-lsd-gdb.log'
 script.write_text('''set pagination off
set confirm off
handle SIGILL stop print nopass
handle SIGTERM nostop noprint pass
printf "LOG_HOOKS_LSD_DEBUG_READY\\n"
continue
python
import gdb
print('LOG_HOOKS_LSD_DEBUG_STOP')
if gdb.selected_inferior().pid:
 gdb.execute('info registers');gdb.execute('x/14i $rip');gdb.execute('bt')
 fp=int(gdb.parse_and_eval('$rbp'))
 for i in range(40):
  try:
   v=bytes(gdb.selected_inferior().read_memory(fp,16));new=int.from_bytes(v[:8],'little');ret=int.from_bytes(v[8:],'little');print('FRAME',hex(fp),hex(ret))
   if new<=fp or new-fp>0x100000:break
   fp=new
  except Exception:break
end
detach
''')
 with out.open('w') as stream:
  debugger=subprocess.Popen(['nsenter','--target',str(pid),'--user','--preserve-credentials','gdb','-q','-nx','-batch','-p',str(pid),'-x',str(script)],stdout=stream,stderr=subprocess.STDOUT)
  deadline=time.monotonic()+30
  while 'LOG_HOOKS_LSD_DEBUG_READY' not in out.read_text():
   if debugger.poll() is not None:raise RuntimeError('Debugger stopped before readiness')
   if time.monotonic()>deadline:raise RuntimeError('Debugger observation timed out; inspect existing handles')
   time.sleep(.1)
  (root/'logs/log-hooks-lsd-live-maps.log').write_text(Path(f'/proc/{pid}/maps').read_text())
  with fifo.open('w') as release:release.write('x\n')
  debugger.wait(timeout=140)
 print('Debugger status',debugger.returncode,'probe status',process.wait(timeout=35))
print(out.read_text()[-6500:])
