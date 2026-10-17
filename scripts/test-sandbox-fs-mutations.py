#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('--capture',action='store_true');args=parser.parse_args()
m=runpy.run_path(str(root/'scripts/sandbox-fs-runtime-profile.py'));p=m['profile'](capture=args.capture)
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
build=root/'runtime/sandbox-fs-mutations-tests';build.mkdir(exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
source='fixtures/hello/sandbox-fs-mutations.c';obj=build/'test.o';binary=build/'test'
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-O0','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','14','14','-syslibroot',str(sdk),'-lSystem',str(obj),'-o',str(binary)],check=True)
(root/'runtime/sandbox-fs-query-enable').write_text('0')
events='logs/sandbox-fs-capture-events.log'
if args.capture:(root/events).write_text('')
mode='capture' if args.capture else 'real';command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root)),mode]
r=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True);text=r.stdout+r.stderr
log='logs/sandbox-fs-mutations-'+mode+'.log';(root/log).write_text(text)
match=re.search(r'SANDBOX_FS_MUTATIONS_NO_SIDE_EFFECTS_OR_FD_LEAKS_OK checks=(\d+) capture=(\d+)',text)
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),mode=mode,command=command,exit_status=r.returncode,
            source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(binary.relative_to(root)),
            log=log,log_sha256=digest(log),checks=int(match[1]) if match else 0,source_sandbox_fs=p['source_sandbox_fs'],
            runtime_execution_verified=r.returncode==0 and match is not None,test_only_query_injection=args.capture,
            profile_application_implemented=False,full_xcode_build_ready=False)
if args.capture:
    rows=[dict(zip(['operation','path','transport','error','decision'],row)) for row in re.findall(r'FS_QUERY operation=(\S+) path=(\S+) transport=(-?\d+) error=(\d+) decision=(\d+)',(root/events).read_text())]
    assert len(rows)==60 and sum(row['decision']=='1' for row in rows)==39
    assert sum(row['error']=='5' for row in rows)==2 and sum(row['transport']=='-11' for row in rows)==1
    assert all('/alias/' not in row['path'] for row in rows)
    record.update(events=events,events_sha256=digest(events),captured_queries=rows,pinned_parent_replacement_checked='SANDBOX_FS_PINNED_PARENT_SURVIVES_PATH_REPLACEMENT_OK' in text)
(root/('artifacts/sandbox-fs-mutations-'+mode+'-test.json')).write_text(json.dumps(record,indent=2)+'\n')
print(r.returncode,text[-5000:]);assert record['runtime_execution_verified']
