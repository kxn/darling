#!/usr/bin/env bash
# Existing Darling/Xcode setup and pinned reference caches are prerequisites.
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
python3 - <<'PY'
from pathlib import Path
import hashlib,json,re,shutil,zipfile,zlib
config=json.loads(Path('config/apple-installer-25G83.json').read_text())
archive=next(Path('runtime/fullsystem/sharedsupport').rglob(config['mobileasset_zip_name']))
with archive.open('rb') as stream:
    if hashlib.file_digest(stream,'sha256').hexdigest()!=config['mobileasset_zip_sha256']:
        raise ValueError('Reference asset ZIP SHA256 mismatch')
destination=Path('runtime/fullsystem/payload-chunks');destination.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(archive) as source:
    parts=sorted((info for info in source.infolist() if re.fullmatch(r'AssetData/payloadv2/payload\.0\d\d',info.filename)),key=lambda info:info.filename)
    if len(parts)!=53:raise ValueError('Unexpected reference payload chunk count')
    for index,info in enumerate(parts):
        target=destination/Path(info.filename).name
        valid=target.is_file() and target.stat().st_size==info.file_size
        if valid:
            crc=0
            with target.open('rb') as stream:
                while block:=stream.read(8*1024*1024):crc=zlib.crc32(block,crc)
            valid=crc==info.CRC
        if not valid:
            partial=target.with_suffix(target.suffix+'.partial')
            with source.open(info) as stream,partial.open('wb') as output:
                shutil.copyfileobj(stream,output,8*1024*1024)
            if partial.stat().st_size!=info.file_size:raise ValueError('Truncated payload chunk')
            partial.replace(target)
        print(f'Payload chunk {index+1}/53 checked',flush=True)
PY
if [[ ! -f 'runtime/recovery-tools/macOS Base System/usr/bin/aa' ]]; then
    runtime/tools/7zip/usr/lib/7zip/7z x -y -oruntime/recovery-tools downloads/recovery/BaseSystem.dmg \
        'macOS Base System/usr/bin/aa' > logs/recovery-aa-extract.log 2>&1
fi
for target in apple-archive-original compression parallel-compression; do
    python3 scripts/rebuild-c-cache-image.py --target "$target" --modern-adapter --lazy-functions \
        > "logs/rebuild-$target.log" 2>&1
done
timeout -k 5 900 bin/darling shell /bin/bash \
    /Volumes/SystemRoot/workspace/scripts/extract-reference-resources-guest.sh \
    > logs/extract-reference-resources.log 2>&1
timeout -k 5 900 bin/darling shell /bin/bash \
    /Volumes/SystemRoot/workspace/scripts/extract-reference-resource-links-guest.sh \
    > logs/extract-reference-resource-links.log 2>&1
python3 scripts/finalize-reference-resources.py
