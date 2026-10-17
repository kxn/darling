#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent;parser=argparse.ArgumentParser();parser.add_argument('--with-data',action='store_true');args=parser.parse_args();label='fixed' if args.with_data else 'baseline'
m=runpy.run_path(str(root/('scripts/icu-data-runtime-profile.py' if args.with_data else 'scripts/mobileasset-query-runtime-profile.py')));p=m['profile']();folder=root/'runtime/icu-data-tests';sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';source='fixtures/hello/icu-data-security.m';obj=folder/(label+'.o');binary=folder/label
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-O0','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','14','14','-syslibroot',str(sdk),'-framework','Foundation','-framework','Security','-framework','CoreFoundation','-licucore','-lobjc','-lSystem',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root)),'/Volumes/SystemRoot/workspace/runtime/icu-data-tests'];command[3]='70';a=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True);text=a.stdout+a.stderr;log='logs/icu-data-security-'+label+'.log';(root/log).write_text(text);digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest();verified=a.returncode==0 and 'SECURITY_RSA_NATIVE_IMPORT_OPENSSL_SHA256_SIGNATURE_AND_TAMPER_REJECTION_OK' in text
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(str(binary.relative_to(root))),source_runtime=p['source_runtime'],original_icu_data=p.get('original_icu_data'),command=command,log=log,log_sha256=digest(log),exit_status=a.returncode,verified=verified,checks=[int(x) for x in re.findall(r'checks=(\d+)',text)],fixture_files={str(n.relative_to(root)):digest(str(n.relative_to(root))) for n in folder.glob('*.bin')},public_key_sha256=digest('runtime/icu-data-tests/public-key.der'),full_xcode_build_ready=False)
(root/('artifacts/icu-data-security-'+label+'.json')).write_text(json.dumps(report,indent=2)+'\n');print(text,flush=True)
if args.with_data:assert verified
else:assert a.returncode==2 and 'ICU_NATIVE_SYSTEM_NUMBER_FORMATTER_NULL' in text
