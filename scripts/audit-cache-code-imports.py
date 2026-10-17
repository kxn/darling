#!/usr/bin/env python3
"""Identify unresolved code references using the pinned cache's export tries.

Optional pinning accepts only a unique public Swift symbol in an original
dependency. It does not implement missing exports or assert runtime readiness.
"""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import re
import runpy

project=Path(__file__).resolve().parent.parent
manifest=project/'config/cache-image-pins.json'
config=json.loads(manifest.read_text())
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--target',choices=sorted(config),required=True)
parser.add_argument('--pin-unique-imports',action='store_true')
args=parser.parse_args();entry=config[args.target]
if entry['reference_set']!='fullsystem':raise ValueError('This audit requires the full reference cache')
source=project/'runtime/fullsystem-libraries'/entry['path'].lstrip('/')
if hashlib.sha256(source.read_bytes()).hexdigest()!=entry['sha256']:
    raise ValueError('Pinned image hash mismatch')
ns=runpy.run_path(str(project/'scripts/dsc-image.py'),init_globals={
    'REFERENCE_CACHE_PATH':project/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT':project/'runtime/fullsystem-libraries'})
ranges=[];owner=''
for line in (project/'runtime/fullsystem/intel-cache-layout.map').read_text().splitlines():
    if line.startswith('/'):owner=line
    match=re.search(r'(__\w+) 0x([\dA-Fa-f]+) -> 0x([\dA-Fa-f]+)',line)
    if match and match[1]!='__LINKEDIT':
        ranges.append((int(match[2],16),int(match[3],16),owner,match[1]))
dependencies={ns['image'](path).path for path in ns['image'](entry['path']).dependencies}
build=project/('runtime/rebuilt-'+args.target)
rows=json.loads((build/'unclassified-code-imports.json').read_text());counts=Counter();pins={}
for row in rows:
    address=int(row['value'],0) if row['value'] else 0
    matches=[(path,segment) for start,end,path,segment in ranges if start<=address<end]
    if len(matches)!=1:
        row['owner']=None;counts[('outside cache',False)]+=1;continue
    path,segment=matches[0];row.update({'owner':path,'segment':segment})
    row['exact_exports']=[name for name,value in ns['image'](path).exports.items()
        if value[0]=='address' and value[1]==address]
    counts[(path,bool(row['exact_exports']))]+=1
    names=row['exact_exports']
    if len(names)==1 and names[0].startswith('_$s') and path in dependencies:
        pins[names[0]]=path
(build/'code-import-audit.json').write_text(json.dumps(rows,indent=2)+'\n')
for (path,exported),count in sorted(counts.items()):
    print(f'{count}: {path}; exact public export={exported}')
if args.pin_unique_imports:
    imports=entry.setdefault('cache_imports',{})
    for name,provider in pins.items():
        if name in imports and imports[name]!=provider:raise ValueError('Conflicting existing import pin: '+name)
    imports.update(dict(sorted(pins.items())))
    temporary=manifest.with_suffix('.json.pending')
    temporary.write_text(json.dumps(config,indent=2)+'\n');temporary.replace(manifest)
    print(f'Pinned {len(pins)} unique original dependency exports; no library installed.')
