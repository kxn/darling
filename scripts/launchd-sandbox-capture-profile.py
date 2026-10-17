#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,runpy
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/launchd-sandbox-source-profile.py'))
def profile(include_system_resources=True,baseline=False):
    p=m['profile'](include_system_resources)
    d=json.loads((root/'artifacts/launchd-sandbox-capture-build.json').read_text())
    digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
    assert d['test_only'] and d['previous_source_runtime']==p['source_runtime']
    for name,sha in d['source_files'].items():assert digest(name)==sha,name
    for item in d['source_runtime'].values():assert digest(item['path'])==item['sha256']
    result={**p,'source_runtime':d['source_runtime'],'test_only_launchd_sandbox_capture':d}
    if baseline:
        b=json.loads((root/'artifacts/launchd-sandbox-capture-baseline-stage.json').read_text())
        assert b['test_only'] and b['previous_source_runtime']==d['source_runtime']
        for key,item in b['source_runtime'].items():
            assert digest(item['path'])==item['sha256']
            assert item['sha256']==(b['baseline_launchd']['sha256'] if key=='LINUXCODE_LAUNCHD' else d['source_runtime'][key]['sha256'])
        result.update(source_runtime=b['source_runtime'],test_only_launchd_sandbox_baseline=b)
    return result
def environment(p):return m['environment'](p)
