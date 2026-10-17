#!/usr/bin/env python3
"""Resolve saved Linux file offsets through the actual x86_64 Mach-O slice.

Universal Darling binaries include a fat-file prefix. A file offset must first
be made relative to the selected slice, then translated through LC_SEGMENT_64;
it is not a symbol's virtual address. The explicit runtime root supplies files
visible through the private prefix overlay, with their map inodes checked.
"""
from pathlib import Path
import argparse,bisect,hashlib,json,re,struct,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('--stem',required=True);parser.add_argument('--runtime-root',required=True);args=parser.parse_args()
runtime=(root/args.runtime_root).resolve();assert runtime.is_relative_to(root/'runtime')
maps=[]
for row in (root/('logs/'+args.stem+'.maps.log')).read_text().splitlines():
    p=row.split(maxsplit=5)
    if len(p)!=6:continue
    lo,hi=[int(x,16) for x in p[0].split('-')]
    maps.append((lo,hi,int(p[2],16),int(p[4]),p[5]))
images={}
def load(path,inode):
    if path.startswith('/workspace/'):file=root/path[len('/workspace/'):]
    elif path.startswith('/state/prefix/'):
        relative=path[len('/state/prefix/'):];file=root/'runtime/state/prefix'/relative
        if not file.is_file():file=runtime/relative
    else:return None
    if not file.is_file():return None
    assert file.stat().st_ino==inode,(path,'Mapped file no longer has the recorded inode')
    data=file.read_bytes();offset=0
    if data[:4]==b'\xca\xfe\xba\xbe':
        arches=[struct.unpack_from('>5I',data,8+20*i) for i in range(struct.unpack_from('>I',data,4)[0])]
        chosen=[a for a in arches if a[0]==0x1000007];assert len(chosen)==1
        offset=chosen[0][2];data=data[offset:offset+chosen[0][3]]
    if data[:4]!=b'\xcf\xfa\xed\xfe':return None
    segments=[];at=32;symbols=[];symtab=None
    for _ in range(struct.unpack_from('<I',data,16)[0]):
        cmd,size=struct.unpack_from('<II',data,at)
        if cmd==0x19:
            addr,length,off,count=struct.unpack_from('<QQQQ',data,at+24)
            if count:segments.append((off,off+count,addr))
        if cmd==2:symtab=struct.unpack_from('<IIII',data,at+8)
        at+=size
    if symtab:
        off,count,stroff,strsize=symtab
        for i in range(count):
            no,kind,section,desc,value=struct.unpack_from('<IBBHQ',data,off+16*i)
            if kind&0xe0 or kind&0xe!=0xe or not no:continue
            symbols.append((value,data[stroff+no:data.index(0,stroff+no)].decode(errors='replace')))
    symbols.sort()
    return dict(file=str(file.relative_to(root)),sha256=hashlib.sha256(file.read_bytes()).hexdigest(),slice_offset=offset,segments=segments,symbols=symbols)
out=[]
for row in (root/('logs/'+args.stem+'.gdb.log')).read_text().splitlines():
    if not row.startswith(('PC ','FRAME ')):out.append(row);continue
    address=int(row.split()[-1],16);mapping=next((s for s in maps if s[0]<=address<s[1]),None)
    if mapping is None:out.append(row);continue
    lo,hi,off,inode,path=mapping
    if path not in images:images[path]=load(path,inode)
    info=images[path]
    if info is None:out.append(row);continue
    fileoff=address-lo+off;local=fileoff-info['slice_offset'];seg=next((s for s in info['segments'] if s[0]<=local<s[1]),None)
    if seg is None:out.append(row);continue
    vmaddr=seg[2]+local-seg[0];symbols=info['symbols'];i=bisect.bisect_right([s[0] for s in symbols],vmaddr)-1
    symbol=symbols[i][1]+'+'+hex(vmaddr-symbols[i][0]) if i>=0 else ''
    out.append(row+' '+info['file']+' fileoff='+hex(fileoff)+' vmaddr='+hex(vmaddr)+' '+symbol)
destination=root/('logs/'+args.stem+'.resolved.log');destination.write_text('\n'.join(out)+'\n')
record={k:{n:v for n,v in d.items() if n!='symbols'} for k,d in images.items() if d}
(root/('artifacts/'+args.stem+'-images.json')).write_text(json.dumps(record,indent=2)+'\n')
print(destination)
