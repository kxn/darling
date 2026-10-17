#!/usr/bin/env python3
"""Replace only iokitd in a private root before its original job is started."""
from pathlib import Path
import argparse,fcntl,hashlib,json,runpy,shutil,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('--baseline',action='store_true');args=parser.parse_args()
p=runpy.run_path(str(root/'scripts/log-compose-runtime-profile.py'))['profile']()
name='artifacts/iokitd-power-'+('baseline-' if args.baseline else '')+'build.json';build=json.loads((root/name).read_text())
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
assert build['full_iokitd_source_build'] and digest(build['binary'])==build['binary_sha256']
folder=root/('runtime/iokitd-power-'+('baseline-runtime' if args.baseline else 'runtime'));folder.mkdir(exist_ok=True)
variant=folder/'darling-root';pending=folder/'darling-root.pending';selected={k:dict(v) for k,v in p['source_runtime'].items()}
server = None
if not args.baseline:
    server = json.loads((root/'artifacts/iokitd-power-server-build.json').read_text())
    assert server['previous_source_runtime'] == p['source_runtime']
    assert digest(server['server']) == server['server_sha256']
    selected['LINUXCODE_DARLING_SERVER'] = dict(path=server['server'],sha256=server['server_sha256'])
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    if pending.exists():shutil.rmtree(pending)
    subprocess.run(['cp','-a','--reflink=auto',str(root/p['source_log_compose']['variant_root']),str(pending)],check=True)
    shutil.copy2(root/build['binary'],pending/'usr/sbin/iokitd')
    for item in selected.values():
        target=folder/Path(item['path']).name;shutil.copy2(root/item['path'],target)
        item.update(path=str(target.relative_to(root)),sha256=digest(target))
    if variant.exists():shutil.rmtree(variant)
    pending.replace(variant)
report=dict(source_ipc_server=server,baseline=args.baseline,source_build=name,source_build_sha256=digest(name),source_iokitd=build,
            previous_source_runtime=p['source_runtime'],source_runtime=selected,variant_root=str(variant.relative_to(root)),
            original_launchd_job_preserved=True,original_job_sha256=digest(variant/'System/Library/LaunchDaemons/org.darlinghq.iokitd.plist'),
            runtime_execution_verified=False,default_entry_promoted=False,full_xcode_build_ready=False)
(root/('artifacts/iokitd-power-'+('baseline-' if args.baseline else '')+'stage.json')).write_text(json.dumps(report,indent=2)+'\n')
print('Staged source iokitd under its original boot job; baseline=',args.baseline)
