#!/usr/bin/env python3
"""Generate deterministic valid image data with the Python standard library."""
from pathlib import Path
import hashlib,json,struct,zlib
root=Path(__file__).resolve().parent.parent;out=root/'runtime/imageio-fixtures';out.mkdir(parents=True,exist_ok=True)
w,h=13,7;pixels=bytes([200,30,90])*(w*h)
def chunk(tag,b):return struct.pack('>I',len(b))+tag+b+struct.pack('>I',zlib.crc32(tag+b))
png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'pHYs',struct.pack('>IIB',2835,2835,1))+chunk(b'IDAT',zlib.compress(b''.join(b'\0'+pixels[y*w*3:(y+1)*w*3] for y in range(h))))+chunk(b'IEND',b'')
gif=b'GIF89a'+struct.pack('<HHBBB',1,1,0x80,0,0)+bytes([0,0,0,255,255,255])+b'\x21\xff\x0bNETSCAPE2.0\x03\x01\x03\x00\x00'+b'\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
# Baseline uncompressed chunky RGB TIFF, with three 8-bit samples.
tags=[(256,4,1,w),(257,4,1,h),(258,3,3,0),(259,3,1,1),(262,3,1,2),(273,4,1,0),(277,3,1,3),(278,4,1,h),(279,4,1,len(pixels)),(284,3,1,1)]
bits=8+2+len(tags)*12+4;strip=bits+6;tags[2]=(258,3,3,bits);tags[5]=(273,4,1,strip)
tiff=b'II'+struct.pack('<HIH',42,8,len(tags))+b''.join(struct.pack('<HHII',*t) for t in tags)+struct.pack('<IHHH',0,8,8,8)+pixels
items=[]
for name,data,width,height,uti in [('test.png',png,w,h,'public.png'),('test.gif',gif,1,1,'com.compuserve.gif'),('test.tiff',tiff,w,h,'public.tiff')]:
 (out/name).write_bytes(data);items.append(dict(path='runtime/imageio-fixtures/'+name,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),width=width,height=height,uti=uti))
(root/'artifacts/imageio-input-fixtures.json').write_text(json.dumps(items,indent=2)+'\n');print('Generated real PNG, GIF loop=3 and uncompressed RGB TIFF')
