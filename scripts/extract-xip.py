#!/usr/bin/env python3
"""Extract the XAR/PBZX/CPIO payload of an Xcode XIP on Linux."""
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import lzma
from pathlib import Path
import struct
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zlib
import argparse

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('input');parser.add_argument('output')
parser.add_argument('--member',default='Content')
parser.add_argument('--report');parser.add_argument('--log')
args=parser.parse_args()
source = Path(args.input).resolve()
destination = Path(args.output).resolve()
destination.mkdir(parents=True, exist_ok=True)
if any(destination.iterdir()):
    sys.exit("Extraction directory must be empty.")

def exact(stream, length):
    data = stream.read(length)
    if len(data) != length:
        raise ValueError("Truncated XIP payload")
    return data

def decode(payload, expected):
    data = lzma.decompress(payload) if payload.startswith(b"\xfd7zXZ\x00") else payload
    if len(data) != expected:
        raise ValueError("PBZX chunk length mismatch")
    return data

started = time.monotonic()
with source.open("rb") as stream:
    magic, header_size, version, compressed_size, toc_size, algorithm = struct.unpack(">IHHQQI", exact(stream, 28))
    if magic != 0x78617221 or version != 1:
        raise ValueError("Unsupported XAR header")
    stream.seek(header_size)
    toc = zlib.decompress(exact(stream, compressed_size))
    if len(toc) != toc_size:
        raise ValueError("XAR table length mismatch")
    root = ET.fromstring(toc)
    content = next(item for item in root.findall("./toc/file") if item.findtext("name") == args.member)
    offset = header_size + compressed_size + int(content.findtext("data/offset"))
    length = int(content.findtext("data/length"))
    end = offset + length
    expected_hash = content.findtext("data/archived-checksum")
    checksum = hashlib.sha1()
    stream.seek(offset)
    header = exact(stream, 12)
    checksum.update(header)
    marker, chunk_size = struct.unpack(">4sQ", header)
    if marker != b"pbzx":
        raise ValueError("Content is not PBZX")
    completed = 0
    total_bytes = 0
    with (Path(args.log) if args.log else destination.parent / "cpio-extract.log").open("wb") as error_log:
        process = subprocess.Popen(
            ["cpio", "-idm", "--no-absolute-filenames", "--no-preserve-owner", "--quiet"],
            cwd=destination, stdin=subprocess.PIPE, stderr=error_log,
        )
        try:
            with ThreadPoolExecutor(max_workers=8) as pool:
                pending = deque()
                while stream.tell() < end or pending:
                    while stream.tell() < end and len(pending) < 16:
                        block_header = exact(stream, 16)
                        checksum.update(block_header)
                        expanded, packed = struct.unpack(">QQ", block_header)
                        if not 0 <= expanded <= chunk_size or packed > end - stream.tell():
                            raise ValueError("Invalid PBZX block")
                        payload = exact(stream, packed)
                        checksum.update(payload)
                        pending.append(pool.submit(decode, payload, expanded))
                    decoded = pending.popleft().result()
                    process.stdin.write(decoded)
                    total_bytes += len(decoded)
                    completed += 1
                    if completed % 32 == 0:
                        print(f"Extracted {total_bytes / 2**30:.2f} GiB ({100 * (stream.tell()-offset) / length:.1f}% compressed input)", flush=True)
            process.stdin.close()
            if process.wait() != 0:
                raise RuntimeError("cpio extraction failed; inspect cpio-extract.log")
        except BaseException:
            process.kill()
            process.wait()
            raise
    if stream.tell() != end or checksum.hexdigest() != expected_hash:
        raise ValueError("XAR Content checksum mismatch")
    result = {
        "source": str(source), "member": args.member, "content_sha1": checksum.hexdigest(),
        "expanded_bytes": total_bytes, "chunks": completed,
        "seconds": round(time.monotonic() - started, 2),
    }
    (Path(args.report) if args.report else destination.parent / "xip-extraction.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
