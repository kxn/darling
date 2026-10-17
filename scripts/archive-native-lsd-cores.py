#!/usr/bin/env python3
"""Keep one owned lsd diagnostic core and discard only its verified duplicates."""
from pathlib import Path
import hashlib, json, shutil, struct, subprocess

root = Path(__file__).resolve().parent.parent
def arguments(path):
    with path.open('rb') as stream:
        header = stream.read(64)
        if header[:6] != b'\x7fELF\x02\x01': return None
        phoff = struct.unpack_from('<Q', header, 32)[0]
        size, count = struct.unpack_from('<HH', header, 54)
        for i in range(count):
            stream.seek(phoff + i * size)
            ph = stream.read(size)
            if struct.unpack_from('<I', ph)[0] != 4: continue
            offset = struct.unpack_from('<Q', ph, 8)[0]
            length = struct.unpack_from('<Q', ph, 32)[0]
            stream.seek(offset)
            notes = stream.read(length)
            at = 0
            while at + 12 <= len(notes):
                namesize, descsize, kind = struct.unpack_from('<III', notes, at)
                name = notes[at + 12:at + 12 + namesize].rstrip(b'\0')
                start = at + 12 + ((namesize + 3) & ~3)
                desc = notes[start:start + descsize]
                if kind == 3 and name == b'CORE' and len(desc) >= 136:
                    return desc[56:136].split(b'\0')[0].decode(errors='replace').strip()
                at = start + ((descsize + 3) & ~3)
    return None

owned = []
for path in (root / 'runtime/state/prefix').glob('core.[0-9]*'):
    args = arguments(path)
    if args and args.startswith('/Volumes/SystemRoot/workspace/runtime/native-lsd/lsd runAsRoot'):
        owned.append((path.stat().st_mtime_ns, path, args))
if not owned:
    print('No duplicate native lsd cores found')
    raise SystemExit(0)
owned.sort()
source = owned[-1][1]
destination = root / 'runtime/native-lsd/lsd-startup.core'
pending = destination.with_suffix('.pending')
subprocess.run(['cp', '--reflink=auto', str(source), str(pending)], check=True)
pending.replace(destination)
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
snapshot = root / 'runtime/native-lsd/crash-runtime'
snapshot.mkdir(exist_ok=True)
shutil.copyfile(root / 'runtime/objc-source/libobjc.A.dylib', snapshot / 'libobjc.A.dylib')
shutil.copyfile(root / 'artifacts/objc-source-build.json', snapshot / 'objc-source-build.json')
report = dict(core=str(destination.relative_to(root)), core_sha256=digest(destination),
    argv=owned[-1][2], deleted_duplicates=[str(path.relative_to(root)) for _, path, _ in owned],
    selection='Only ELF CORE/NT_PRPSINFO argv matching the exact staged native lsd command.',
    runtime_snapshot={str(p.relative_to(root)): digest(p) for p in snapshot.iterdir() if p.is_file()})
(root / 'artifacts/native-lsd-core-archive.json').write_text(json.dumps(report, indent=2) + '\n')
for _, path, _ in owned: path.unlink()
print('Archived one native lsd core and removed', len(owned), 'verified duplicate cores')
