#!/usr/bin/env python3
"""Observe receive-right releases and a later libdispatch trap in live lsd."""
from pathlib import Path
import json,re,subprocess,time
root=Path(__file__).resolve().parent.parent
match=b'/Volumes/SystemRoot/workspace/runtime/native-lsd/lsd';pid=None
for _ in range(250):
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:argv=(p/'cmdline').read_bytes().split(b'\0')[0]
        except OSError:continue
        if argv==match:pid=p.name;break
    if pid:break
    time.sleep(.1)
assert pid,'No live lsd appeared'
segments=[]
for _ in range(250):
    maps=Path('/proc/'+pid+'/maps').read_text()
    for row in maps.splitlines():
        p=row.split(maxsplit=5)
        if len(p)==6 and p[-1].endswith('/usr/lib/system/libsystem_kernel.dylib'):
            lo,hi=[int(s,16) for s in p[0].split('-')];segments.append((lo,hi,int(p[2],16)))
    if segments:break
    time.sleep(.05)
assert segments
base=min(lo-off for lo,hi,off in segments)
library=root/'runtime/dispatch-workloop-source/darling-root/usr/lib/system/libsystem_kernel.dylib'
symbols={p[2]:int(p[0],16) for row in subprocess.check_output(['llvm-nm-19','--defined-only',str(library)],text=True).splitlines() if len(p:=row.split())==3}
script=root/'runtime/dispatch-workloop-source/trace-lsd-ports.gdb'
python='''import gdb,struct
def frames():
 f=int(gdb.parse_and_eval('$rbp'))
 for i in range(22):
  try:n,pc=struct.unpack('<QQ',gdb.selected_inferior().read_memory(f,16).tobytes())
  except Exception:break
  print('FRAME',hex(f),hex(pc))
  if n<=f or n>f+0x100000:break
  f=n
class Release(gdb.Breakpoint):
 def __init__(self,address,name):
  super().__init__('*'+hex(address),internal=True);self.name=name
 def stop(self):
  if self.name=='mod_refs' and (int(gdb.parse_and_eval('$edx'))!=1 or int(gdb.parse_and_eval('(int)$ecx'))>=0):return False
  print('PORT_RELEASE',self.name,'thread',gdb.selected_thread().ptid,'port',int(gdb.parse_and_eval('$esi')),'right',int(gdb.parse_and_eval('$edx')),'delta',int(gdb.parse_and_eval('(int)$ecx')))
  frames();return False
'''
for symbol,name in [('_mach_port_mod_refs','mod_refs'),('_mach_port_destroy','destroy'),('_mach_port_destruct','destruct')]:python+='Release('+str(base+symbols[symbol])+','+repr(name)+')\n'
script.write_text('set pagination off\nhandle SIGILL stop print nopass\npython\n'+python+'end\ncontinue\np $_siginfo\ninfo registers\nx/12gx $rdi\nprintf \"VANISHED_PORT %u\\n\", *(unsigned int *)($rdi+24)\npython\nframes()\nopen('+repr(str(root/'logs/lsd-port-lifetime.maps.log'))+",'w').write(open('/proc/"+pid+"/maps').read())\nend\n")
print('Tracing live lsd',pid,flush=True)
result=subprocess.run(['gdb','-q','-batch','-p',pid,'-x',str(script)],capture_output=True,text=True,timeout=50)
(root/'logs/lsd-port-lifetime.gdb.log').write_text(result.stdout+result.stderr)
print((result.stdout+result.stderr)[-6500:],flush=True)
