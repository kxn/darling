#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,runpy
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/unrestricted-sandbox-runtime-profile.py'))
def profile(include_system_resources=True):
    p=m['profile'](include_system_resources)
    d=json.loads((root/'artifacts/coreservices-unrestricted-diagnostic-stage.json').read_text())
    digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
    assert d['test_only'] and d['diagnostic_policy_overrides_original'] and d['previous_source_runtime']==p['source_runtime']
    for key in ['original_policy','selected_policy']:assert digest(d[key])==d[key+'_sha256']
    for item in d['source_runtime'].values():assert digest(item['path'])==item['sha256']
    return {**p,'source_runtime':d['source_runtime'],'coreservices_diagnostic_policy':d}
def environment(p):return m['environment'](p)
