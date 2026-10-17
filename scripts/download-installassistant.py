#!/usr/bin/env python3
"""Download the Apple 25G83 full installer in resumable, checked HTTP ranges.

The product URL/size and TOC digest are pinned from Apple's update catalog.
This downloads data only; it never runs the macOS installer.
"""
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import hashlib,json,struct,time,urllib.request,zlib

project=Path(__file__).resolve().parent.parent
manifest=json.loads((project/'config/apple-installer-25G83.json').read_text())
url=manifest['url']
assert manifest['length']==18384624402 and manifest['build']=='25G83'
assert url.startswith('https://swcdn.apple.com/content/downloads/37/33/140-93587-A_GRFFH93NOL/')
length=manifest['length'];chunk_size=16*1024*1024
parts=project/'downloads/installassistant-25G83-ranges';parts.mkdir(parents=True,exist_ok=True)
count=(length+chunk_size-1)//chunk_size

def fetch(index):
    start=index*chunk_size;end=min(length,start+chunk_size)-1
    path=parts/f'{index:05d}'
    if path.exists() and path.stat().st_size==end-start+1:return
    for attempt in range(12):
        try:
            request=urllib.request.Request(url+f'?linuxcode-range={start}&attempt={attempt}',
                headers={'Range':f'bytes={start}-{end}'})
            with urllib.request.urlopen(request,timeout=45) as response:
                if response.status!=206 or response.headers.get('Content-Range')!=f'bytes {start}-{end}/{length}':
                    raise ValueError('Server did not honor requested range')
                data=response.read(end-start+2)
            if len(data)!=end-start+1:raise ValueError('Truncated or oversized range')
            path.with_suffix('.part').write_bytes(data);path.with_suffix('.part').replace(path)
            return
        except Exception:
            if attempt==11:raise
            time.sleep(min(attempt+1,5))

destination=project/'downloads/InstallAssistant-25G83.pkg'
sha1=hashlib.sha1();sha256=hashlib.sha256()
if destination.exists():
    assert destination.stat().st_size==length
    print('Verifying existing installer.',flush=True)
    with destination.open('rb') as stream:
        while data:=stream.read(chunk_size):sha1.update(data);sha256.update(data)
else:
    started=time.monotonic();last=started
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures=[pool.submit(fetch,i) for i in range(count)]
        for done,future in enumerate(as_completed(futures),1):
            future.result()
            if time.monotonic()-last>=10 or done==count:
                print(f'Installer download: {done}/{count} ranges ({done*chunk_size/2**30:.2f} GiB), {time.monotonic()-started:.0f}s',flush=True)
                last=time.monotonic()
    print('Assembling and hashing the complete installer.',flush=True)
    with destination.with_suffix('.part').open('wb') as stream:
        for index in range(count):
            data=(parts/f'{index:05d}').read_bytes();stream.write(data);sha1.update(data);sha256.update(data)
    assert destination.with_suffix('.part').stat().st_size==length
    destination.with_suffix('.part').replace(destination)
if sha256.hexdigest()!=manifest['package_sha256']:
    raise ValueError('Complete installer SHA256 mismatch')
with destination.open('rb') as stream:
    magic,header,version,toc_length,toc_size,algorithm=struct.unpack('>4sHHQQI',stream.read(28))
    assert magic==b'xar!' and version==1 and algorithm==1
    stream.seek(header);compressed=stream.read(toc_length)
    assert len(zlib.decompress(compressed))==toc_size
toc_digest=hashlib.sha1(compressed).hexdigest()
if manifest['catalog_toc_sha1']!=toc_digest:
    raise ValueError('XAR TOC does not match the pinned Apple catalog digest')
report={'source':url,'product':'140-93587','build':'25G83','version':'26.6.2',
    'length':length,'sha1':sha1.hexdigest(),'sha256':sha256.hexdigest(),
    'xar_toc_sha1':toc_digest,'catalog_digest_verified':True,'catalog_digest_kind':'xar-toc-sha1',
    'cms_signature_verified':False,'installer_executed':False}
(project/'artifacts/installassistant-download.json').write_text(json.dumps(report,indent=2)+'\n')
print('Full installer downloaded and catalog digest verified; no installer executed.',flush=True)
