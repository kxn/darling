#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,runpy
root=Path(__file__).resolve().parent.parent;parent=runpy.run_path(str(root/'scripts/icu-data-runtime-profile.py'))
def profile(include_system_resources=True,diagnostic=False):
 p=parent['profile'](include_system_resources,diagnostic);d=json.loads((root/'artifacts/fatal-signal-stage.json').read_text());digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
 assert digest(d['kernel_build'])==d['kernel_build_sha256']
 for item in d['source_kernel']['sources']:assert digest(item['source'])==item['sha256'],item['source']
 chosen=d['runtimes']['diagnostic' if diagnostic else 'normal'];assert chosen['previous_source_runtime']==p['source_runtime']
 for item in chosen['source_runtime'].values():assert digest(item['path'])==item['sha256']
 assert digest(chosen['policy'])==chosen['policy_sha256']
 for n,sha in p['icu_data_selected_runtime']['resources'].items():
  name=str(Path(chosen['variant_root'])/'usr/share/icu'/Path(n).name);assert digest(name)==sha,name
 return {**p,'source_runtime':chosen['source_runtime'],'source_fatal_signal':d,'fatal_signal_selected_runtime':chosen}
def environment(p):return parent['environment'](p)
