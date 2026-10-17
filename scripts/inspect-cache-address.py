#!/usr/bin/env python3
"""Read-only owner/symbol inspection in the pinned full Intel reference cache."""
from pathlib import Path
import bisect
import re
import runpy
import subprocess
import sys

project=Path(__file__).resolve().parent.parent
ns=runpy.run_path(str(project/'scripts/dsc-image.py'),init_globals={
    'REFERENCE_CACHE_PATH':project/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT':project/'runtime/fullsystem-libraries'})
ranges=[];owner=''
for line in (project/'runtime/fullsystem/intel-cache-layout.map').read_text().splitlines():
    if line.startswith('/'):owner=line
    match=re.search(r'(__\w+) 0x([\dA-Fa-f]+) -> 0x([\dA-Fa-f]+)',line)
    if match and match[1]!='__LINKEDIT':ranges.append((int(match[2],16),int(match[3],16),owner,match[1]))
for argument in sys.argv[1:]:
    address=int(argument,0)
    print(hex(address),'raw',ns['read'](address,48).hex(' '))
    for start,end,path,segment in ranges:
        if not start<=address<end:continue
        print(path,segment,'+',hex(address-start))
        exported=ns['image'](path).exports
        exact=[name for name,value in exported.items() if value[0]=='address' and value[1]==address]
        if exact:print('Exact exports:',', '.join(exact[:8]))
        source=project/'runtime/fullsystem-libraries'/path.lstrip('/')
        rows=[]
        for line in subprocess.check_output(['llvm-nm-19','--defined-only','--numeric-sort',str(source)],text=True).splitlines():
            parts=line.split()
            if len(parts)!=3:continue
            try:rows.append((int(parts[0],16),parts[-1]))
            except ValueError:pass
        index=bisect.bisect_right([value for value,_ in rows],address)
        for value,name in rows[max(0,index-2):index+2]:print(hex(value),name)
