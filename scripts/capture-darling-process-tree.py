#!/usr/bin/env python3
"""Read Darling descendants across its nested PID namespaces and real pipe owners."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,subprocess,time
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('--stem',required=True);parser.add_argument('--wait-xcrun',type=int,default=0);parser.add_argument('--stacks',action='store_true');args=parser.parse_args()
started=time.monotonic();snapshots=[];captures=[]
while True:
 allrows={};servers=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   status=(p/'status').read_text();pid=int(p.name);parent=int(next(l.split()[1] for l in status.splitlines() if l.startswith('PPid:')));comm=(p/'comm').read_text().strip()
   allrows[pid]=(p,parent,comm,status)
   if comm=='darlingserver':servers.append(pid)
  except (OSError,StopIteration):pass
 if len(servers)!=1:
  if snapshots:break
  raise SystemExit('Expected one live Darling server: '+repr(servers))
 selected={servers[0]}
 while True:
  previous=len(selected);selected.update(pid for pid,(_,parent,_,_) in allrows.items() if parent in selected)
  if len(selected)==previous:break
 rows=[]
 for pid in sorted(selected):
  p,parent,comm,status=allrows[pid]
  try:
   row=dict(host_pid=pid,host_parent=parent,comm=comm,status=status,pid_namespace=os.readlink(p/'ns/pid'),argv=[s.decode(errors='replace') for s in (p/'cmdline').read_bytes().split(b'\0') if s],fds={},threads=[])
   for fd in (p/'fd').iterdir():
    try:row['fds'][fd.name]=dict(target=os.readlink(fd),info=(p/'fdinfo'/fd.name).read_text())
    except OSError:pass
   for t in (p/'task').iterdir():
    item=dict(host_tid=int(t.name))
    for name in ['stat','wchan','syscall','children']:
     try:item[name]=(t/name).read_text()
     except OSError:pass
    row['threads'].append(item)
   rows.append(row)
  except OSError:pass
 snapshots.append(dict(checked_at=datetime.now(timezone.utc).isoformat(),elapsed=time.monotonic()-started,processes=rows))
 (root/('artifacts/'+args.stem+'-live.json')).write_text(json.dumps(dict(selected_by_server_parentage=True,snapshots=snapshots),indent=2)+'\n')
 targets=[r for r in rows if r['argv'] and any(s in r['argv'][0].lower() for s in ['xcrun','metal','coresimulatorservice','securityd'])]
 if any(r['argv'] and 'xcrun' in r['argv'][0].lower() for r in targets) or not args.wait_xcrun or time.monotonic()-started>=args.wait_xcrun:break
 time.sleep(2)
if args.stacks:
 targets += [r for r in rows if r['argv'] and r['argv'][0]=='/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild']
 code="""import gdb,struct
for t in gdb.selected_inferior().threads():
 t.switch();print('THREAD',t.ptid);print('PC',hex(int(gdb.parse_and_eval('$rip'))));f=int(gdb.parse_and_eval('$rbp'))
 for i in range(55):
  try:n,pc=struct.unpack('<QQ',gdb.selected_inferior().read_memory(f,16).tobytes())
  except Exception:break
  print('FRAME',hex(f),hex(pc))
  if n<=f or n>f+0x100000:break
  f=n
"""
 for row in targets:
  pid=row['host_pid'];stem=args.stem+'-'+str(pid)
  try:
   maps=Path('/proc/'+str(pid)+'/maps').read_text();r=subprocess.run(['gdb','-q','-nx','-batch','-ex','set pagination off','-ex','python exec('+repr(code)+')','-p',str(pid)],capture_output=True,text=True,timeout=15)
   raw='logs/'+stem+'.gdb.log';mapname='logs/'+stem+'.maps.log';(root/raw).write_text(r.stdout+r.stderr);(root/mapname).write_text(maps)
   captures.append(dict(host_pid=pid,argv=row['argv'],stem=stem,exit_status=r.returncode,raw=raw,maps=mapname))
  except (OSError,subprocess.TimeoutExpired) as e:captures.append(dict(host_pid=pid,error=str(e)))
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
for row in captures:
 for name in ['raw','maps']:
  if name in row:row[name+'_sha256']=digest(row[name])
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),selected_by_server_parentage=True,snapshots=snapshots,captures=captures,script='scripts/capture-darling-process-tree.py',script_sha256=digest('scripts/capture-darling-process-tree.py'))
output='artifacts/'+args.stem+'-process-tree.json';(root/output).write_text(json.dumps(report,indent=2)+'\n')
print(output)
for r in rows:
 if r['comm']=='mldr':print(r['host_pid'],r['host_parent'],r['argv'][:8])
