#!/usr/bin/env python3
"""Read suspended Darling server contexts; do not call functions in the inferior."""
from pathlib import Path
import argparse,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('--stem',required=True);parser.add_argument('--server-binary');args=parser.parse_args()
pids=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  if (p/'comm').read_text().strip()=='darlingserver':pids.append(p.name)
 except OSError:pass
assert len(pids)==1,pids
pid=pids[0];maps=Path('/proc/'+pid+'/maps').read_text();base=int(next(x for x in maps.splitlines() if '/usr/bin/darlingserver' in x and x.split()[2]=='00000000').split('-')[0],16)
(root/('logs/'+args.stem+'.maps.log')).write_text(maps)
server=(root/args.server_binary) if args.server_binary else Path('/proc/'+pid+'/root/usr/bin/darlingserver')
assert server.is_file()
assert server.stat().st_ino==int(next(x for x in maps.splitlines() if '/usr/bin/darlingserver' in x).split()[4])
code=r'''import gdb,sys,struct,re
sys.path.insert(0,'/usr/share/gcc/python')
from libstdcxx.v6.printers import register_libstdcxx_printers
try:register_libstdcxx_printers(None)
except Exception:pass
r=gdb.parse_and_eval("&'DarlingServer::threadRegistry()::registry'").cast(gdb.lookup_type("DarlingServer::Registry<DarlingServer::Thread>").pointer()).dereference()
table=r['_map']['_M_h'];node=table['_M_before_begin']['_M_nxt'];pair=table.type.template_argument(1)
fields={f.name:f for f in pair.fields()};first=fields['first'];second=fields['second']
shared_type=second.type;values=[]
while int(node):
 address=int(node);values.append((int(gdb.Value(address+node.dereference().type.sizeof+first.bitpos//8).cast(first.type.pointer()).dereference()),gdb.Value(address+node.dereference().type.sizeof+second.bitpos//8).cast(shared_type.pointer()).dereference()))
 node=node.dereference()['_M_nxt']
for key,value in values:
 try:
  t=value['_M_ptr'].dereference();assert int(t['_tid'])==key;p=t['_process']['_M_ptr'].dereference();ns=int(p['_nspid'])
  print('SERVER_TASK',ns,'thread',t['_nstid'],'address',value['_M_ptr'],'active',t['_activeCall']['_M_ptr'],'running',t['_running'],'suspended',t['_suspended'],'defer',t['_deferReplyForS2C'],'processingSignal',t['_processingSignal'])
  for field in ['_s2cPerformSempahore','_s2cReplySempahore','_s2cInterruptEnterSemaphore','_s2cInterruptExitSemaphore']:
   print(field,t[field].dereference(),'count',t[field].dereference()['xnu_semaphore'].dereference()['count'])
  regs=t['_resumeContext']['uc_mcontext']['gregs'];pc=int(regs[16]);fp=int(regs[10]);print('SERVER_RESUME',hex(pc),hex(fp))
  if t['_suspended']:
   names=['r8','r9','r10','r11','r12','r13','r14','r15','rdi','rsi','rbp','rbx','rdx','rax','rcx','rsp','rip']
   saved={n:int(gdb.parse_and_eval('$'+n)) for n in names}
   try:
    for i,n in enumerate(names):gdb.execute('set $'+n+' = '+hex(int(regs[i]) & ((1<<64)-1)),to_string=True)
    trace=gdb.execute('bt 28',to_string=True);print(trace)
    for address in re.findall(r'_s2cPerform \(this=(?:this@entry=)?(0x[0-9a-f]+)',trace):
     target=gdb.Value(int(address,16)).cast(gdb.lookup_type('DarlingServer::Thread').pointer()).dereference()
     print('S2C_TARGET',address,'tid',target['_tid'],'nsid',target['_nstid'],'dead',target['_dead'],'process',target['_process']['_M_ptr'].dereference()['_nspid'],'active',target['_activeCall']['_M_ptr'],'pending',target['_pendingCall']['_M_ptr'],'reply_count',target['_s2cReplySempahore'].dereference()['xnu_semaphore'].dereference()['count'])
   finally:
    for n,a in saved.items():gdb.execute('set $'+n+' = '+hex(a & ((1<<64)-1)),to_string=True)
 except Exception as e:print('READ_ERROR',str(e))
'''
script=root/'runtime/core-volume-trace'/('server-state-'+args.stem+'.py');script.write_text(code)
command=['gdb','-q','-nx','-batch','-ex','add-symbol-file '+str(server)+' -o '+hex(base),'-p',pid,'-ex','source '+str(script),'-ex','detach']
a=subprocess.run(command,capture_output=True,text=True,timeout=15);text=a.stdout+a.stderr;(root/('logs/'+args.stem+'.gdb.log')).write_text(text);print(text[-20000:]);assert not a.returncode and 'SERVER_TASK' in text and 'Python Exception' not in text
