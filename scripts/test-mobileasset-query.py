#!/usr/bin/env python3
"""Verify original query ABI, real absent-service errors and keyed XPC results."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent;m=runpy.run_path(str(root/'scripts/mobileasset-query-runtime-profile.py'));p=m['profile']();folder=root/'runtime/mobileasset-query-tests';folder.mkdir(exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';include=root/'vendor/darling/src/private-frameworks/MobileAsset/include';source='fixtures/hello/mobileasset-query.m';binary=folder/'native';obj=folder/'native.o'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-I',str(include),'-fblocks','-O0','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-F',str(root/'runtime/mobileasset-query-source/frameworks'),'-framework','MobileAsset','-framework','Foundation','-lSystem','-lobjc',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))];command[3]='100'
a=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True);text=a.stdout+a.stderr;log='logs/mobileasset-query-native-test.log';(root/log).write_text(text);digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
markers=['MOBILEASSET_QUERY_REAL_ABSENT_SERVICE_SYNC_ASYNC_TYPED_ERRORS_NO_FAKE_SUCCESS_OK','MOBILEASSET_QUERY_REAL_48_XPC_REPLIES_4_THREADS_32_ASYNC_QUERIES_8_DETACHED_CALLBACKS_OK','MOBILEASSET_QUERY_PROTOCOL_KEYED_FILTERS_RESULTS_METADATA_ERRORS_48_REAL_REQUESTS_OK']
d=dict(checked_at=datetime.now(timezone.utc).isoformat(),source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(str(binary.relative_to(root))),command=command,source_mobileasset_query=p['source_mobileasset_query'],source_runtime=p['source_runtime'],log=log,log_sha256=digest(log),exit_status=a.returncode,checks=sum(map(int,re.findall(r'checks=(\d+)',text))),verified=a.returncode==0 and all(s in text for s in markers),actual_named_XPC_test_peer=True,actual_Apple_mobileassetd=False,download_implemented=False,full_xcode_build_ready=False)
(root/'artifacts/mobileasset-query-native-test.json').write_text(json.dumps(d,indent=2)+'\n');print(text,flush=True);assert d['verified']
