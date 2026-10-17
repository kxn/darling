#!/usr/bin/env python3
"""Inspect a verified additional Apple recovery image for the missing Intel library."""
from pathlib import Path
import hashlib,importlib.util,json,plistlib,subprocess,os
root=Path(__file__).resolve().parent.parent;image=root/'downloads/img4-older-recovery/BaseSystem.dmg';chunklist=image.with_suffix('.chunklist')
spec=importlib.util.spec_from_file_location('macrecovery',root/'vendor/macrecovery/macrecovery.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.verify_image(str(image),str(chunklist))
seven=root/'runtime/tools/7zip/usr/lib/7zip/7z';listing='logs/img4-older-recovery-list.log';result=subprocess.run([str(seven),'l','-slt',str(image)],capture_output=True,text=True,check=True);(root/listing).write_text(result.stdout+result.stderr)
paths=[line.removeprefix('Path = ') for line in result.stdout.splitlines() if line.startswith('Path = ')]
selected=[name for name in paths if name.endswith('/System/Library/CoreServices/SystemVersion.plist') or name.endswith('/usr/lib/libimg4.dylib') or '/System/Library/dyld/dyld_shared_cache_x86_64' in name]
assert selected,'No Intel recovery members found in the actual image inventory'
destination=root/'runtime/img4-older-recovery';destination.mkdir(exist_ok=True)
with (root/'logs/img4-older-recovery-extract.log').open('w') as stream:subprocess.run([str(seven),'x','-y','-o'+str(destination),str(image),*selected],stdout=stream,stderr=subprocess.STDOUT,check=True)
version_files=list(destination.rglob('SystemVersion.plist'));assert len(version_files)==1;version=plistlib.loads(version_files[0].read_bytes());print('Additional Intel reference version:',version,flush=True)
files=list(destination.rglob('libimg4.dylib'));caches=[p for p in destination.rglob('dyld_shared_cache_x86_64*') if p.is_file()]
digest=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
record=dict(recovery_image=str(image.relative_to(root)),recovery_image_sha256=digest(image),chunklist=str(chunklist.relative_to(root)),chunklist_sha256=digest(chunklist),Apple_chunklist_verification_passed=True,listing=listing,listing_sha256=digest(root/listing),selected_members=selected,system_version=version,extracted_libimg4=[str(p.relative_to(root)) for p in files],extracted_symlinks={str(p.relative_to(root)):os.readlink(p) for p in files if p.is_symlink()},Intel_cache_files={str(p.relative_to(root)):digest(p) for p in caches},scope='Read-only reference extraction on Linux; not an installed or booted operating system')
(root/'artifacts/img4-older-recovery-reference.json').write_text(json.dumps(record,indent=2)+'\n');print('Standalone libimg4 files:',record['extracted_libimg4']);print('Intel cache count:',len(caches))
