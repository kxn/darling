#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,runpy,shutil,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/quarantine-vfs-runtime-profile.py'));p=m['profile'](False)
build=root/'runtime/quarantine-vfs-test';build.mkdir(exist_ok=True);output=build/'output'
if output.exists():shutil.rmtree(output)
output.mkdir();sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
sources=['fixtures/hello/quarantine-vfs-source.c','fixtures/hello/quarantine-vfs-leaf.c']
for name,source in zip(['test','leaf'],sources):
    obj=build/(name+'.o');binary=build/name
    subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-c',str(root/source),'-o',str(obj)],check=True)
    subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-lSystem',str(obj),'-o',str(binary)],check=True)
guest=lambda path:'/Volumes/SystemRoot/workspace/'+str(path.relative_to(root));digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest();rows=[]
for control in [True,False]:
    profile=m['profile'](False,old_kernel_control=control);label='old-kernel-control' if control else 'source'
    command=profile['command'][:-2]+[guest(build/'test'),guest(output),guest(build/'leaf'),label];log='logs/quarantine-vfs-'+label+'.log'
    with (root/log).open('w') as stream:r=subprocess.run(command,env=m['environment'](profile),stdout=stream,stderr=subprocess.STDOUT)
    text=(root/log).read_text();print(label,r.returncode,text[-5000:],flush=True);rows.append(dict(label=label,command=command,exit_status=r.returncode,log=log,log_sha256=digest(log)))
    if r.returncode:break
labels={}
if all(row['exit_status']==0 for row in rows) and len(rows)==2:
    for name in ['new','existing','directory','renamed','fork-inherited','exec-inherited']:
        labels[name]=os.getxattr(output/name,'user.com.apple.quarantine').decode();print('Host physical xattr',name,labels[name])
    assert labels['new'].startswith('0082;') and labels['directory'].startswith('0086;00000000;') and labels['renamed'].startswith('0082;')
    assert os.getxattr(output/'new','user.user.com.apple.quarantine')==b'shadow'
    assert 'user.com.apple.quarantine' not in os.listxattr(output/'parent-unconfined-exec')
    # hard and hard-link are one inode; the unconfined parent's removal affects both.
    assert 'user.com.apple.quarantine' not in os.listxattr(output/'hard-link')
success=len(rows)==2 and all(row['exit_status']==0 for row in rows) and bool(labels)
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'sources':{n:digest(n) for n in sources},'binaries':{str((build/n).relative_to(root)):digest(str((build/n).relative_to(root))) for n in ['test','leaf']},'checks':rows,'physical_Linux_xattrs':labels,'real_policy_and_VFS_execution_verified':success,'full_xcode_build_ready':False}
(root/'artifacts/quarantine-vfs-source-test.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if success else 1)
