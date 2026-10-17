#!/usr/bin/env python3
"""Bind libSystem's public unfair locks to libplatform, avoiding kernel weak stubs.

Only Darling's open source runtime is changed. Preserve all existing exports and
library ordinals; rebuild the export trie and append it to __LINKEDIT.
"""
from pathlib import Path
import struct

project = Path(__file__).resolve().parent.parent
guest = project / 'runtime/rootfs/usr/libexec/darling'
target = guest / 'usr/lib/libSystem.B.dylib'
backup = project / 'runtime/compat-backups/libSystem.B.dylib'
if not backup.exists():
    backup.write_bytes(target.read_bytes())
data = backup.read_bytes()
if data[:4] == b'\xca\xfe\xba\xbe':
    for i in range(struct.unpack_from('>I', data, 4)[0]):
        cpu, subtype, offset, size, align = struct.unpack_from('>IIIII', data, 8 + 20*i)
        if cpu == 0x01000007:
            data = data[offset:offset+size]
            break
binary = bytearray(data)
assert binary[:4] == b'\xcf\xfa\xed\xfe', 'Expected x86_64 Mach-O'

def uleb(value):
    result = bytearray()
    while value >= 128:
        result.append((value & 127) | 128)
        value >>= 7
    result.append(value)
    return bytes(result)

def read_uleb(data, cursor):
    result = shift = 0
    while True:
        byte = data[cursor]
        cursor += 1
        result |= (byte & 127) << shift
        if byte < 128:
            return result, cursor
        shift += 7

cursor = 32
ordinal = 0
for _ in range(struct.unpack_from('<I', binary, 16)[0]):
    command, size = struct.unpack_from('<II', binary, cursor)
    if command in (0xc, 0x18, 0x80000018, 0x8000001f, 0x80000023):
        ordinal += 1
        name_offset = struct.unpack_from('<I', binary, cursor+8)[0]
        name = binary[cursor+name_offset:cursor+size].split(b'\0')[0]
        if name == b'/usr/lib/system/libsystem_platform.dylib':
            platform_ordinal = ordinal
    if command in (0x22, 0x80000022):
        export_command = cursor + 40
    elif command == 0x80000033:
        export_command = cursor + 8
    if command == 0x19 and binary[cursor+8:cursor+24].rstrip(b'\0') == b'__LINKEDIT':
        linkedit_command = cursor
    cursor += size
offset, size = struct.unpack_from('<II', binary, export_command)
trie = binary[offset:offset+size]
exports = {}

def visit(position, prefix=b''):
    terminal_size, cursor = read_uleb(trie, position)
    if terminal_size:
        exports[prefix] = bytes(trie[cursor:cursor+terminal_size])
    cursor += terminal_size
    children = trie[cursor]
    cursor += 1
    for _ in range(children):
        end = trie.index(0, cursor)
        edge = bytes(trie[cursor:end])
        child, cursor = read_uleb(trie, end+1)
        visit(child, prefix+edge)

visit(0)
for name in (b'_os_unfair_lock_lock', b'_os_unfair_lock_unlock'):
    exports[name] = uleb(8) + uleb(platform_ordinal) + b'\0'

# Build a radix tree, retaining the original terminal payloads verbatim.
nodes = []
def make_node(items, prefix):
    node = {'terminal': exports.get(prefix, b''), 'children': [], 'offset': 0}
    nodes.append(node)
    remaining = [name for name in items if name != prefix]
    for first in sorted(set(name[len(prefix)] for name in remaining)):
        group = [name for name in remaining if name[len(prefix)] == first]
        common = group[0]
        for name in group[1:]:
            index = len(prefix)
            while index < min(len(common), len(name)) and common[index] == name[index]:
                index += 1
            common = common[:index]
        child = make_node(group, common)
        node['children'].append((common[len(prefix):], child))
    return node
make_node(list(exports), b'')

def encode(node):
    value = uleb(len(node['terminal'])) + node['terminal'] + bytes([len(node['children'])])
    for edge, child in node['children']:
        value += edge + b'\0' + uleb(child['offset'])
    return value

for _ in range(100):
    cursor = 0
    changed = False
    for node in nodes:
        changed |= node['offset'] != cursor
        node['offset'] = cursor
        cursor += len(encode(node))
    if not changed:
        break
else:
    raise RuntimeError('Trie offsets did not converge')
new_trie = b''.join(encode(node) for node in nodes)
binary.extend(b'\0' * (-len(binary) % 8))
new_offset = len(binary)
binary.extend(new_trie)
struct.pack_into('<II', binary, export_command, new_offset, len(new_trie))
fileoff = struct.unpack_from('<Q', binary, linkedit_command+40)[0]
filesize = len(binary)-fileoff
struct.pack_into('<Q', binary, linkedit_command+48, filesize)
struct.pack_into('<Q', binary, linkedit_command+32, (filesize+4095) & ~4095)
target.write_bytes(binary)
print(f'Bound two public unfair-lock exports to libplatform (ordinal {platform_ordinal}); preserved {len(exports)-2} other exports.')
