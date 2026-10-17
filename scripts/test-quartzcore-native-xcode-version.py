#!/usr/bin/env python3
"""Keep the original version command working in the expanded native experiment."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-dyld',action='store_true')
parser.add_argument('--source-mobileasset',action='store_true')
parser.add_argument('--native-systeminfo',action='store_true')
parser.add_argument('--source-security-policy',action='store_true')
parser.add_argument('--pthread-yield-export',action='store_true');args=parser.parse_args()
if args.source_mobileasset and not args.source_dyld:parser.error('--source-mobileasset requires --source-dyld')
if args.native_systeminfo and not args.source_mobileasset:parser.error('--native-systeminfo requires --source-mobileasset')
if args.source_security_policy and not args.native_systeminfo:parser.error('--source-security-policy requires --native-systeminfo')
if args.pthread_yield_export and not args.source_security_policy:parser.error('--pthread-yield-export requires --source-security-policy')
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
probe_path='artifacts/pthread-yield-export-xcode-probe.json' if args.pthread_yield_export else 'artifacts/security-policy-source-xcode-probe.json' if args.source_security_policy else 'artifacts/apple-system-info-native-xcode-probe.json' if args.native_systeminfo else 'artifacts/mobileasset-source-xcode-probe.json' if args.source_mobileasset else 'artifacts/quartzcore-native-source-dyld-probe.json' if args.source_dyld else 'artifacts/quartzcore-native-probe.json'
probe=json.loads((root/probe_path).read_text())
environment=os.environ.copy()
for variable,item in probe['source_runtime'].items():
    assert digest(item['path'])==item['sha256'];environment[variable]=str(root/item['path'])
command=list(probe['command']);assert command[-1]=='-showsdks';command[-1]='-version'
log=root/('logs/pthread-yield-export-xcode-version.log' if args.pthread_yield_export else 'logs/security-policy-source-xcode-version.log' if args.source_security_policy else 'logs/apple-system-info-native-xcode-version.log' if args.native_systeminfo else 'logs/mobileasset-source-xcode-version.log' if args.source_mobileasset else 'logs/quartzcore-native-source-dyld-xcode-version.log' if args.source_dyld else 'logs/quartzcore-native-xcode-version.log')
with log.open('w') as stream:
    result=subprocess.run(command,cwd=root,env=environment,stdout=stream,stderr=subprocess.STDOUT)
text=log.read_text()
assert result.returncode==0 and 'Xcode 26.6\n' in text and 'Build version 17F113\n' in text
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),original_xcode_version_verified=True,
    exit_status=result.returncode,command=command,selected_runtime=probe['source_runtime'],
    probe_sha256=digest(probe_path),
    driver_sha256=digest('scripts/test-quartzcore-native-xcode-version.py'),
    log=str(log.relative_to(root)),log_sha256=digest(log),full_xcode_build_ready=False,signing_ready=False)
(root/('artifacts/pthread-yield-export-xcode-version.json' if args.pthread_yield_export else 'artifacts/security-policy-source-xcode-version.json' if args.source_security_policy else 'artifacts/apple-system-info-native-xcode-version.json' if args.native_systeminfo else 'artifacts/mobileasset-source-xcode-version.json' if args.source_mobileasset else 'artifacts/quartzcore-native-source-dyld-xcode-version.json' if args.source_dyld else 'artifacts/quartzcore-native-xcode-version.json')).write_text(json.dumps(report,indent=2)+'\n')
print('Original Xcode 26.6/17F113 version query passed with the selected source runtime and framework profile')
