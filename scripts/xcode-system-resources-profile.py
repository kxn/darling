#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,runpy
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/log-pack-profile.py'));environment=m['environment']
def profile():
    p=m['profile']();stage=json.loads((root/'artifacts/xcode-system-resources-stage.json').read_text())
    assert stage['prefix_links_published'],'Original package dependency closure is pending; publish the prefix explicitly before this experimental profile'
    digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
    assert digest(stage['package'])==stage['package_sha256']
    for name,sha in stage['payload_files'].items():assert digest(name)==sha,name
    for name,target in {**stage['prefix_links'],**stage['payload_symlinks']}.items():assert os.readlink(root/name)==target,name
    return {**p,'xcode_system_resources':stage}
