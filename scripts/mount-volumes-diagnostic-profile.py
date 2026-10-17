#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,runpy
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/mount-flags-runtime-profile.py'))
def profile():
 p=m['profile']();d=json.loads((root/'artifacts/mount-volumes-diagnostic-stage.json').read_text());digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
 assert d['test_only'] and d['diagnostic_policy_overrides_original'] and d['previous_source_runtime']==p['source_runtime']
 for key in ['original_policy','selected_policy']:assert digest(d[key])==d[key+'_sha256']
 for v in d['source_runtime'].values():assert digest(v['path'])==v['sha256']
 return {**p,'source_runtime':d['source_runtime'],'mount_volumes_diagnostic':d}
def environment(p):return m['environment'](p)
