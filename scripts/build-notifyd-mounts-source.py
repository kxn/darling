#!/usr/bin/env python3
"""Build all pinned notifyd sources and both MIG servers, without the package binary."""
from pathlib import Path
import hashlib,json,subprocess
root=Path(__file__).resolve().parent.parent
repo=root/'vendor/darling/src/external/libnotify'
commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip();assert commit=='98156d3f847a3ced6c5f52c12a889047bc4f9b20'
build=root/'runtime/notifyd-mounts-source';build.mkdir(exist_ok=True);gen=build/'generated';gen.mkdir(exist_ok=True)
iokit=json.loads((root/'artifacts/iokitd-matching-build.json').read_text());original=iokit['sources'][0]['command'];common=original[:original.index('-c')];common=[a for a in common if not a.startswith(('-std=','-stdlib='))]
common+=['-DPLATFORM_MacOSX','-I'+str(repo),'-I'+str(repo/'notifyd'),'-I'+str(gen),'-DSINGLE_THREADED_NOTIFY_STATE=1','-DMACH_NOTIFY_SEND_POSSIBLE_EXPECTED=1','-include','sys/fileport.h','-Wno-incompatible-function-pointer-types','-Wno-int-conversion']
mig=root/'runtime/darlingserver-source-build/build-mig';sdk=common[common.index('-isysroot')+1]
for name in ['notify_ipc','notify']:
    subprocess.run([str(mig),'-arch','x86_64','-target','x86_64-apple-macos11','-isysroot',sdk,'-nostdinc',*[a for a in common if a.startswith(('-I','-D'))],'-user',str(gen/(name+'User.c')),'-header',str(gen/(name+'.h')),'-server',str(gen/(name+'Server.c')),'-sheader',str(gen/(name+'Server.h')),str(repo/'notifyd'/(name+'.defs'))],check=True)
paths=[repo/'notifyd'/n for n in ['notifyd.c','notify_proc.c','pathwatch.c','service.c','mountwatch.c']]+[gen/'notify_ipcServer.c',gen/'notifyServer.c']
objects=[];sources=[]
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n,path in enumerate(paths):
    obj=build/(str(n)+'-'+path.stem+'.o');command=[*common,'-c',str(path),'-o',str(obj)];print('Compile',path.relative_to(root),flush=True);subprocess.run(command,check=True);objects.append(obj);sources.append(dict(source=str(path.relative_to(root)),sha256=digest(path),command=command))
guest=root/'runtime/rootfs/usr/libexec/darling';binary=build/'notifyd'
command=['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(guest),'-o',str(binary),*map(str,objects),'-L'+str(guest/'usr/lib'),'-lSystem','-lbsm.0'];subprocess.run(command,check=True)
d=dict(source_commit=commit,complete_source_files=len(paths),sources=sources,headers={str(p.relative_to(root)):digest(p) for p in list(repo.glob('*.h'))+list((repo/'notifyd').glob('*.h'))+[repo/'notifyd/CMakeLists.txt',repo/'notifyd/notify.defs',repo/'notifyd/notify_ipc.defs']},binary=str(binary.relative_to(root)),binary_sha256=digest(binary),link_command=command,full_notifyd_source_build=True,Linux_mount_namespace_monitor=True,XPC_matching_publisher_implemented=False,direct_Mach_transport_implemented=True,runtime_execution_verified=False,full_xcode_build_ready=False)
(root/'artifacts/notifyd-mounts-build.json').write_text(json.dumps(d,indent=2)+'\n');print('Built full notifyd',len(paths))
