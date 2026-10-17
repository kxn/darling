#!/usr/bin/env python3
"""Run public Darwin metadata APIs with independent Linux filesystem fixtures."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,runpy,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--mount-path-kernel',action='store_true');args=parser.parse_args()
label='mount-path-metadata-kernel' if args.mount_path_kernel else 'metadata-kernel'
work=root/'runtime/metadata-fixture';work.mkdir(exist_ok=True)
(work/'item.bin').write_bytes(bytes(i%251 for i in range(1234)))
os.setxattr(work/'item.bin','user.com.apple.FinderInfo',bytes((i*7+3)%256 for i in range(32)))
os.setxattr(work/'item.bin','user.com.apple.ResourceFork',b'R'*259)
with (work/'sparse.bin').open('wb') as f:f.truncate(104857600)
(work/'children').mkdir(exist_ok=True)
(work/'bulk').mkdir(exist_ok=True)
for i in range(35):(work/'bulk'/('file-'+str(i)+'-'+'x'*(i%13))).write_bytes(bytes(range(i)))
(work/'bulk'/'subdirectory').mkdir(exist_ok=True)
if not (work/'bulk'/'symlink').is_symlink():(work/'bulk'/'symlink').symlink_to('file-0-')
(work/'empty').mkdir(exist_ok=True)
(work/'single').mkdir(exist_ok=True)
(work/'single'/'1234567').touch()
for name in ['one','two']:(work/'children'/name).touch()
if not (work/'link').is_symlink():(work/'link').symlink_to('item.bin')
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';guest=root/'runtime/rootfs/usr/libexec/darling'
commands=[['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-Wno-deprecated-declarations','-c','fixtures/hello/metadata-kernel.c','-o','artifacts/metadata-kernel.o'],['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(guest),'-lSystem','artifacts/metadata-kernel.o','-o','artifacts/metadata-kernel']]
for c in commands:subprocess.run(c,cwd=root,check=True)
m=runpy.run_path(str(root/('scripts/mount-path-kernel-profile.py' if args.mount_path_kernel else 'scripts/metadata-kernel-profile.py')));p=m['profile']();command=p['command'][:7]+['/Volumes/SystemRoot/workspace/artifacts/metadata-kernel','/Volumes/SystemRoot/workspace/runtime/metadata-fixture']
r=subprocess.run(command,cwd=root,env=m['environment'](p),capture_output=True,text=True)
log='logs/'+label+'-test.log';(root/log).write_text(r.stdout+r.stderr)
digest=lambda s:hashlib.sha256((root/s).read_bytes()).hexdigest()
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),command=command,build_commands=commands,source_runtime=p['source_runtime'],source_kernel=p['source_kernel'],exit_status=r.returncode,log=log,log_sha256=digest(log),source_sha256=digest('fixtures/hello/metadata-kernel.c'),binary_sha256=digest('artifacts/metadata-kernel'),runtime_execution_verified=r.returncode==0 and 'METADATA_KERNEL_PASS' in r.stdout)
(root/('artifacts/'+label+'-test.json')).write_text(json.dumps(report,indent=2)+'\n');print(r.stdout+r.stderr,end='');raise SystemExit(r.returncode)
