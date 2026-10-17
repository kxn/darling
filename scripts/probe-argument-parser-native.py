#!/usr/bin/env python3
"""Check actual original parser loading; the shared probe writes to stderr."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent;m=runpy.run_path(str(root/'scripts/argument-parser-native-profile.py'));p=m['profile']()
binary='runtime/device-identity-native/load';source='fixtures/hello/native-foundation-load.c'
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+binary,'/System/Library/PrivateFrameworks/ArgumentParserInternal.framework/Versions/A/ArgumentParserInternal']
r=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True);text=r.stdout+r.stderr;log='logs/argument-parser-native-load.log';(root/log).write_text(text)
verified=r.returncode==0 and 'NATIVE_FOUNDATION_PROBE_MAIN_ENTERED' in text and 'NATIVE_FOUNDATION_DLOPEN_COMPLETED' in text
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),command=command,exit_status=r.returncode,log=log,log_sha256=digest(log),stage=p['native_argument_parser'],source_runtime=p['source_runtime'],probe_binary=binary,probe_binary_sha256=digest(binary),probe_source=source,probe_source_sha256=digest(source),native_dlopen_verified=verified,full_parser_semantics_verified=False)
(root/'artifacts/argument-parser-native-load.json').write_text(json.dumps(record,indent=2)+'\n');print(r.returncode,text);raise SystemExit(0 if verified else 1)
