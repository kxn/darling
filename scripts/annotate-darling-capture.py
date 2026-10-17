#!/usr/bin/env python3
"""Resolve retained frame addresses, including full Objective-C method names."""
from pathlib import Path
import argparse,bisect,re,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('stem');args=parser.parse_args()
raw=(root/('logs/'+args.stem+'.gdb.log')).read_text();maps=(root/('logs/'+args.stem+'.maps.log')).read_text();segments=[]
for line in maps.splitlines():
    fields=line.split(maxsplit=5)
    if len(fields)!=6:continue
    start,end=[int(x,16) for x in fields[0].split('-')];segments.append((start,end,int(fields[2],16),fields[5]))
def translate(path):
    for prefix,where in [('/workspace/',root),('/state/prefix/',root/'runtime/state/prefix'),('/usr/libexec/darling/',root/'runtime/rootfs/usr/libexec/darling')]:
        if path.startswith(prefix):return where/path[len(prefix):]
cache={};output=[]
for line in raw.splitlines():
    if not line.startswith(('FRAME ','PC ')):output.append(line);continue
    address=int(line.split()[-1],16);segment=next((s for s in segments if s[0]<=address<s[1]),None)
    if not segment:output.append(line);continue
    start,end,offset,path=segment;fileoff=address-start+offset;file=translate(path);symbol=''
    if file and file.is_file():
        if file not in cache:
            result=subprocess.run(['llvm-nm-19','--numeric-sort',str(file)],capture_output=True,text=True,check=True)
            symbols=[]
            for row in result.stdout.splitlines():
                match=re.match(r'^([0-9a-fA-F]+)\s+\S\s+(.*)$',row)
                if match:symbols.append((int(match[1],16),match[2]))
            cache[file]=symbols
        symbols=cache[file];index=bisect.bisect_right([s[0] for s in symbols],fileoff)-1
        if index>=0:symbol=symbols[index][1]+'+'+hex(fileoff-symbols[index][0])
    output.append(line+' '+path+' fileoff='+hex(fileoff)+' '+symbol)
destination=root/('logs/'+args.stem+'.symbols.log');destination.write_text('\n'.join(output)+'\n');print(destination)
