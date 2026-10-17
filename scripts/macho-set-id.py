#!/usr/bin/env python3
"""Change an LC_ID_DYLIB name in place without moving Mach-O data."""
from pathlib import Path
import struct
import sys

path = Path(sys.argv[1])
name = sys.argv[2].encode() + b"\0"
data = bytearray(path.read_bytes())

def patch(offset):
    magic = bytes(data[offset:offset + 4])
    endian = "<" if magic in (b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe") else ">"
    wide = magic in (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf")
    commands = struct.unpack_from(endian + "I", data, offset + 16)[0]
    cursor = offset + (32 if wide else 28)
    for _ in range(commands):
        command, length = struct.unpack_from(endian + "II", data, cursor)
        if command == 0xD:
            start = cursor + struct.unpack_from(endian + "I", data, cursor + 8)[0]
            capacity = cursor + length - start
            if len(name) > capacity:
                raise ValueError("Replacement install name does not fit existing command")
            data[start:start + capacity] = name.ljust(capacity, b"\0")
            return
        cursor += length
    raise ValueError("LC_ID_DYLIB not found")

magic = bytes(data[:4])
if magic in (b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca"):
    endian = ">" if magic == b"\xca\xfe\xba\xbe" else "<"
    count = struct.unpack_from(endian + "I", data, 4)[0]
    for index in range(count):
        offset = struct.unpack_from(endian + "I", data, 8 + index * 20 + 8)[0]
        patch(offset)
else:
    patch(0)
path.write_bytes(data)
