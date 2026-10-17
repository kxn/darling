#!/usr/bin/env python3
"""Compile the unmodified Apple SDK interface client and run original AppleArchive."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,subprocess
parser=argparse.ArgumentParser();parser.add_argument("--corecrypto-hkdf",action="store_true");parser.add_argument("--native-crypto",action="store_true");args=parser.parse_args()
root=Path(__file__).resolve().parent.parent;m=runpy.run_path(str(root/('scripts/commoncrypto-original-profile.py' if args.native_crypto else 'scripts/corecrypto-hkdf-profile.py' if args.corecrypto_hkdf else 'scripts/applearchive-native-profile.py')));p=m['profile']();environment=m['environment'](p);guest='/Volumes/SystemRoot/workspace/'
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';sdk_guest='/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';toolchain='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain';digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-O2','-c','fixtures/hello/applearchive-native-owner.c','-o','artifacts/applearchive-native-owner.o'],cwd=root,check=True)
steps=[('compile',[toolchain+'/usr/bin/swift-frontend','-c',guest+'fixtures/hello/applearchive-native.swift','-target','x86_64-apple-macos14.0','-sdk',sdk_guest,'-module-name','OriginalAppleArchiveNativeProbe','-o',guest+'artifacts/applearchive-native.o']),('link',[toolchain+'/usr/bin/clang','-target','x86_64-apple-macos14.0','-isysroot',sdk_guest,guest+'artifacts/applearchive-native.o',guest+'artifacts/applearchive-native-owner.o','-L/usr/lib/swift','-lswiftCore','-lswiftSwiftOnoneSupport','-lswiftAppleArchive','-lswiftSystem','-framework','Foundation','-framework','CryptoKit','-Wl,-rpath,/usr/lib/swift','-o',guest+'artifacts/applearchive-native']),('execute',[guest+'artifacts/applearchive-native'])]
checks=[]
for name,tail in steps:
 command=p['command'][:-2]+tail
 if name=='compile':command[3]='180'
 r=subprocess.run(command,cwd=root,env=environment,capture_output=True,text=True);log='logs/applearchive-native-'+('original-' if args.native_crypto else 'hkdf-' if args.corecrypto_hkdf else '')+name+'.log';(root/log).write_text(r.stdout+r.stderr);print(name,r.returncode,r.stdout+r.stderr,flush=True);checks.append(dict(step=name,command=command,exit_status=r.returncode,log=log,log_sha256=digest(log)))
 if r.returncode:break
verified=len(checks)==3 and checks[-1]['exit_status']==0 and 'NATIVE_APPLEARCHIVE_STREAMS_OK' in (root/checks[-1]['log']).read_text()
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'runtime_execution_verified':verified,'original_Apple_SDK_interface_used':True,'sources':{n:digest(n) for n in ['fixtures/hello/applearchive-native.swift','fixtures/hello/applearchive-native-owner.c']},'full_AppleArchive_compatibility':False}
for name in ['artifacts/applearchive-native.o','artifacts/applearchive-native']:
 if (root/name).exists():record.setdefault('binaries',{})[name]=digest(name)
(root/('artifacts/applearchive-native-'+('original-' if args.native_crypto else 'hkdf-' if args.corecrypto_hkdf else '')+'test.json')).write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if verified else 1)
