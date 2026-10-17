#!/usr/bin/env python3
"""Independently verify every code page against each cache's CodeDirectory.

These Apple cache signatures are ad hoc and have no CMS signer. This verifies
content integrity after decompression, not an Apple certificate chain.
"""
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import hashlib,json,mmap,struct,sys

project=Path(__file__).resolve().parent.parent
def verify_cache(path):
    with path.open('rb') as stream,mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as data:
        if not data[:16].startswith(b'dyld_v1 x86_64h'):raise ValueError('Unexpected cache architecture')
        offset,size=struct.unpack_from('<QQ',data,40)
        if offset+size!=len(data):raise ValueError('Invalid cache signature range')
        magic,length,count=struct.unpack_from('>III',data,offset)
        if magic!=0xfade0cc0 or length>size or count>16:raise ValueError('Invalid embedded signature')
        directory=None;cms=False
        for index in range(count):
            slot,relative=struct.unpack_from('>II',data,offset+12+index*8)
            at=offset+relative;kind,blob_length=struct.unpack_from('>II',data,at)
            if relative+blob_length>length:raise ValueError('Signature blob out of bounds')
            if slot==0 and kind==0xfade0c02:directory=bytes(data[at:at+blob_length])
            if slot==0x10000 and kind==0xfade0b01 and blob_length>8:cms=True
        if directory is None:raise ValueError('Missing primary CodeDirectory')
        version,flags,hash_offset,ident,special,slots,limit=struct.unpack_from('>7I',directory,8)
        hash_size,hash_type,platform,page_log=struct.unpack_from('4B',directory,36)
        if version!=0x20400 or hash_type!=2 or hash_size!=32 or page_log!=12:
            raise ValueError('Unsupported CodeDirectory layout/hash')
        if struct.unpack_from('>I',directory,44)[0]:raise ValueError('Scatter vectors are unsupported')
        page_size=1<<page_log
        if limit!=offset or (limit+page_size-1)//page_size!=slots:raise ValueError('CodeDirectory does not cover cache contents')
        if hash_offset+slots*hash_size>len(directory):raise ValueError('Page hash table out of bounds')
        for index in range(slots):
            chunk=data[index*page_size:min((index+1)*page_size,limit)]
            expected=directory[hash_offset+index*32:hash_offset+(index+1)*32]
            if hashlib.sha256(chunk).digest()!=expected:
                raise ValueError(f'{path.name}: CodeDirectory mismatch at page {index}')
        return {'file':path.name,'length':len(data),'code_pages':slots,'page_size':page_size,
            'all_code_pages_verified':True,'code_directory_sha256':hashlib.sha256(directory).hexdigest(),
            'ad_hoc':bool(flags&2),'cms_signer_present':cms,'cms_signature_verified':False}

def main():
    root=project/'runtime/fullsystem/intel-cache'
    paths=[Path(arg) for arg in sys.argv[1:]] if len(sys.argv)>1 else sorted(root.glob('dyld_shared_cache_x86_64h*'))
    if not paths:raise ValueError('No decoded Intel cache files')
    reports=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for future in as_completed([pool.submit(verify_cache,path) for path in paths]):
            report=future.result();reports.append(report)
            print(f"Verified {report['file']}: {report['code_pages']} code pages (ad hoc, no CMS signer)",flush=True)
    if len(sys.argv)==1:
        if len(reports)!=7:raise ValueError('Expected main cache and six subcaches')
        (project/'artifacts/intel-cache-page-verification.json').write_text(json.dumps({
            'files':sorted(reports,key=lambda report:report['file']),
            'total_code_pages':sum(report['code_pages'] for report in reports),
            'all_code_pages_verified':True,'apple_certificate_chain_verified':False,
            'scope':'Independent SHA256 integrity checks of decompressed cache contents. Whole APFS-image SHA384 mismatch remains unresolved.'
        },indent=2)+'\n')
if __name__=='__main__':main()
