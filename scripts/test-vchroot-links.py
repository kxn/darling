#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,re,runpy,subprocess
parser=argparse.ArgumentParser();parser.add_argument('--baseline',action='store_true');args=parser.parse_args()
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/('scripts/global-fsevents-runtime-profile.py' if args.baseline else 'scripts/vchroot-links-runtime-profile.py')));p=m['profile']()
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';build=root/'runtime/vchroot-links-tests';build.mkdir(exist_ok=True);obj=build/'links.o';binary=build/'links';source='fixtures/hello/vchroot-links.c'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-c',source,'-o',str(obj)],cwd=root,check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-lSystem',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))]+(['baseline'] if args.baseline else []);log='logs/vchroot-links-'+('baseline' if args.baseline else 'fixed')+'.log'
with (root/log).open('w') as stream:r=subprocess.run(command,env=m['environment'](p),cwd=root,stdout=stream,stderr=subprocess.STDOUT)
text=(root/log).read_text();print(text[-4000:],end='');digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
passed=r.returncode==2 and 'BASELINE_LINKS_33 result=0' in text if args.baseline else r.returncode==0 and 'VCHROOT_LINKS_LIMIT_BOUNDS_GUARD_AND_64K_STACK_OK' in text
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),source_runtime=p['source_runtime'],source_vchroot_links=p.get('source_vchroot_links'),command=command,log=log,log_sha256=digest(log),exit_status=r.returncode,checks=[int(v) for v in re.findall(r'checks=(\d+)',text)],verified=passed)
(root/('artifacts/vchroot-links-'+('baseline' if args.baseline else 'fixed')+'.json')).write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if passed else 1)
