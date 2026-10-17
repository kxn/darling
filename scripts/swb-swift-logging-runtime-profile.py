#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,runpy
root=Path(__file__).resolve().parent.parent;parent=runpy.run_path(str(root/'scripts/swb-logging-runtime-profile.py'))
def profile(include_system_resources=True,diagnostic=False):
 p=parent['profile'](include_system_resources,diagnostic);d=json.loads((root/'artifacts/swb-swift-logging-stage.json').read_text());digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
 for field in ['source','reconstruction']:assert digest(d[field])==d[field+'_sha256']
 chosen=d['runtimes']['diagnostic' if diagnostic else 'normal'];assert chosen['previous_source_runtime']==p['source_runtime']
 for n,sha in chosen['files'].items():assert digest(n)==sha,n
 for item in chosen['source_runtime'].values():assert digest(item['path'])==item['sha256']
 return {**p,'source_runtime':chosen['source_runtime'],'original_swb_swift_logging':d,'swb_swift_logging_selected_runtime':chosen}
def environment(p):return parent['environment'](p)
