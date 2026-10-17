#!/usr/bin/env python3
"""Resolve captured frame-pointer return addresses using actual mapped Mach-O files."""
from pathlib import Path
import argparse, bisect, hashlib, json, re, struct

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('log')
parser.add_argument('--output', required=True)
args = parser.parse_args()
text = (root / args.log).read_text()
mappings = []
for line in text.splitlines():
    m = re.match(r'(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+0x[0-9a-f]+\s+(0x[0-9a-f]+)\s+(?:[rwxps-]{4}\s+)?(/.+?)\s*$', line)
    if m: mappings.append((int(m[1], 16), int(m[2], 16), m[4]))
def actual(path):
    if path.startswith('/workspace/'): return root / path[len('/workspace/'):]
    if path.startswith('/state/prefix/'):
        candidate = root / 'runtime/state/prefix' / path[len('/state/prefix/'):]
        if candidate.is_file(): return candidate
        path = '/' + path[len('/state/prefix/'):]
    for base in ['runtime/state/prefix', 'runtime/libdyld-source/darling-root']:
        candidate = root / base / path.lstrip('/')
        if candidate.is_file(): return candidate
    return None
cache = {}
def image(path):
    if path in cache: return cache[path]
    filename = actual(path)
    if filename is None: return None
    original = filename.read_bytes()
    data = original
    if data[:4] == b'\xca\xfe\xba\xbe':
        for i in range(struct.unpack_from('>I', data, 4)[0]):
            cpu, sub, offset, size, alignment = struct.unpack_from('>5I', data, 8 + 20 * i)
            if cpu == 0x1000007:
                data = data[offset:offset + size]
                break
    if data[:4] != b'\xcf\xfa\xed\xfe': return None
    at = 32
    symtab = None
    for _ in range(struct.unpack_from('<I', data, 16)[0]):
        cmd, size = struct.unpack_from('<II', data, at)
        if cmd == 0x19 and data[at + 8:at + 24].split(b'\0')[0] == b'__TEXT':
            preferred = struct.unpack_from('<Q', data, at + 24)[0]
        if cmd == 2: symtab = struct.unpack_from('<IIII', data, at + 8)
        at += size
    symbols = []
    if symtab:
        off, count, stroff, strsize = symtab
        for i in range(count):
            no, kind, section, desc, value = struct.unpack_from('<IBBHQ', data, off + i * 16)
            if kind & 0xe == 0xe and not kind & 0xe0:
                name = data[stroff + no:data.index(0, stroff + no)].decode()
                symbols.append((value, name))
    symbols.sort()
    base = min(start for start, end, name in mappings if name == path) - preferred
    result = (base, symbols, str(filename.relative_to(root)), hashlib.sha256(original).hexdigest())
    cache[path] = result
    return result
frames = []
records = re.findall(r'MACH_FRAME (\d+) (0x[0-9a-f]+) (0x[0-9a-f]+)', text)
pc = re.search(r'^rip\s+(0x[0-9a-f]+)', text, re.M)
if pc: records.insert(0, ('-1', 'current-PC', pc[1]))
for number, fp, pc in records:
    address = int(pc, 16)
    owner = next((p for a, b, p in mappings if a <= address < b), None)
    record = dict(index=int(number), frame_pointer=fp, return_address=pc, mapped_image=owner)
    info = image(owner) if owner else None
    if info:
        base, symbols, filename, sha = info
        target = address - base
        at = bisect.bisect_right(symbols, (target, chr(0x10ffff))) - 1
        record.update(image=filename, image_sha256=sha, image_relative_address=hex(target))
        if at >= 0:
            value, name = symbols[at]
            record.update(nearest_symbol=name, symbol_offset=hex(target - value))
    frames.append(record)
    print(record['index'], owner, record.get('nearest_symbol'), record.get('symbol_offset'))
report = dict(log=args.log, log_sha256=hashlib.sha256((root / args.log).read_bytes()).hexdigest(),
    method='Captured real frame-pointer chain and mapping ranges; nearest retained Mach-O nlist symbol with explicit offset.', frames=frames)
(root / args.output).write_text(json.dumps(report, indent=2) + '\n')
