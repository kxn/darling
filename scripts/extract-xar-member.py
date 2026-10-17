#!/usr/bin/env python3
"""Copy a raw XAR member or bounded bzip2 metadata, verifying both checksums.

This reads data only and does not execute package scripts or verify CMS trust.
"""
from pathlib import Path
import bz2,hashlib,json,struct,sys,xml.etree.ElementTree as ET,zlib

if len(sys.argv)!=4:raise SystemExit('Usage: extract-xar-member.py package member output')
source=Path(sys.argv[1]);destination=Path(sys.argv[3])
with source.open('rb') as stream:
    magic,header,version,compressed_size,toc_size,algorithm=struct.unpack('>4sHHQQI',stream.read(28))
    assert magic==b'xar!' and version==1 and algorithm==1
    stream.seek(header);compressed=stream.read(compressed_size);xml=zlib.decompress(compressed)
    assert len(xml)==toc_size
    root=ET.fromstring(xml)
    checksum=root.find('./toc/checksum');assert checksum.attrib['style']=='sha1'
    stream.seek(header+compressed_size+int(checksum.findtext('offset')))
    assert stream.read(int(checksum.findtext('size')))==hashlib.sha1(compressed).digest()
    nodes=[n for n in root.findall('./toc/file') if n.findtext('name')==sys.argv[2]]
    assert len(nodes)==1
    data=nodes[0].find('data');encoding=data.find('encoding').attrib['style'];assert encoding in ['application/octet-stream','application/x-bzip2']
    length=int(data.findtext('length'));expanded_length=int(data.findtext('size'))
    if encoding=='application/octet-stream':assert length==expanded_length
    else:assert max(length,expanded_length)<=64*1024*1024,'Compressed metadata member exceeds supported bound'
    archived=data.find('archived-checksum');extracted=data.find('extracted-checksum')
    assert archived.attrib['style']==extracted.attrib['style']=='sha1'
    stream.seek(header+compressed_size+int(data.findtext('offset')))
    remaining=length;sha1=hashlib.sha1();sha256=hashlib.sha256()
    destination.parent.mkdir(parents=True,exist_ok=True)
    partial=destination.with_suffix(destination.suffix+'.part')
    with partial.open('wb') as output:
        while remaining:
            chunk=stream.read(min(16*1024*1024,remaining))
            if not chunk:raise ValueError('Truncated XAR member')
            output.write(chunk);sha1.update(chunk);sha256.update(chunk);remaining-=len(chunk)
    if sha1.hexdigest()!=archived.text:raise ValueError('XAR content checksum mismatch')
    if encoding=='application/x-bzip2':
        payload=bz2.decompress(partial.read_bytes())
        assert len(payload)==expanded_length and hashlib.sha1(payload).hexdigest()==extracted.text
        partial.write_bytes(payload);sha256=hashlib.sha256(payload)
    else:assert sha1.hexdigest()==extracted.text
    partial.replace(destination)
    report={'source':str(source),'member':sys.argv[2],'length':length,'sha1':sha1.hexdigest(),
        'sha256':sha256.hexdigest(),'expanded_length':expanded_length,'encoding':encoding,'extracted_sha1':extracted.text,'xar_content_checksums_verified':True,'cms_signature_verified':False}
    destination.with_suffix(destination.suffix+'.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
