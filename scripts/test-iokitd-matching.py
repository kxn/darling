#!/usr/bin/env python3
"""Run actual production registry/MIG objects with test-only controllable services."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
build=json.loads((root/'artifacts/iokitd-matching-build.json').read_text())
folder=root/'runtime/iokitd-matching-tests';folder.mkdir(exist_ok=True)
source='fixtures/hello/iokit-matching-harness.mm';client='fixtures/hello/iokit-matching-client.c'
command=list(build['sources'][0]['command']);command[command.index('-c')+1]=str(root/source);command[command.index('-o')+1]=str(folder/'harness.o')
subprocess.run(command,check=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-O0','-Wno-deprecated-declarations','-c',str(root/client),'-o',str(folder/'client.o')],check=True)
user=next(i for i in build['sources'] if i['source'].endswith('/iokitmigServer.c'));user_command=list(user['command']);user_command[user_command.index('-c')+1]=str((root/user['source']).with_name('iokitmigUser.c'));user_command[user_command.index('-o')+1]=str(folder/'user.o');subprocess.run(user_command,check=True)
link=list(build['link_command']);link[link.index('-o')+1]=str(folder/'test');link+=['-e','_matching_test_main',str(folder/'harness.o'),str(folder/'client.o'),str(folder/'user.o'),'-framework','IOKit'];subprocess.run(link,check=True)
m=runpy.run_path(str(root/'scripts/iokitd-matching-runtime-profile.py'));p=m['profile']()
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str((folder/'test').relative_to(root))]
a=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True);text=a.stdout+a.stderr
log='logs/iokitd-matching-test.log';(root/log).write_text(text);digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
match=re.search(r'IOKIT_MATCHING_NATIVE_CALLBACKS_OK checks=(\d+) callbacks=(\d+) cycles=128',text)
d=dict(checked_at=datetime.now(timezone.utc).isoformat(),command=command,exit_status=a.returncode,source=source,source_sha256=digest(source),client=client,client_sha256=digest(client),binary=str((folder/'test').relative_to(root)),binary_sha256=digest(folder/'test'),log=log,log_sha256=digest(log),source_build='artifacts/iokitd-matching-build.json',source_build_sha256=digest('artifacts/iokitd-matching-build.json'),production_object_files_reused=build['complete_source_files'],test_only_services=True,fixtures_installed_in_production=False,checks=int(match[1]) if match else 0,callbacks=int(match[2]) if match else 0,lifetime_cycles=128,runtime_execution_verified=a.returncode==0 and match is not None,source_iokitd_matching=p['source_iokitd_matching'],linux_hardware_hotplug_verified=False,full_xcode_build_ready=False)
(root/'artifacts/iokitd-matching-test.json').write_text(json.dumps(d,indent=2)+'\n');print(text);assert d['runtime_execution_verified']
