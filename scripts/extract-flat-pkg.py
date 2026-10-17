#!/usr/bin/env python3
"""Extract a gzip/CPIO payload from a flat XAR package on Linux.

Checks the payload's archived checksum. Does not validate the installer CMS.
"""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
import zlib

if len(sys.argv) != 3:
    sys.exit('Usage: extract-flat-pkg.py package.pkg empty-output-directory')
source = Path(sys.argv[1]).resolve()
destination = Path(sys.argv[2]).resolve()
destination.mkdir(parents=True, exist_ok=True)
if any(destination.iterdir()):
    sys.exit('Extraction directory must be empty.')
with source.open('rb') as stream:
    magic, header_size, version, toc_length, toc_size, algorithm = struct.unpack('>IHHQQI', stream.read(28))
    assert magic == 0x78617221 and version == 1
    stream.seek(header_size)
    xml = zlib.decompress(stream.read(toc_length))
    assert len(xml) == toc_size
    root = ET.fromstring(xml)
    payloads = [node for node in root.findall('.//file') if node.findtext('name') == 'Payload']
    if len(payloads) != 1:
        sys.exit('Expected exactly one package payload.')
    data = payloads[0].find('data')
    offset = header_size + toc_length + int(data.findtext('offset'))
    remaining = int(data.findtext('length'))
    expected = data.find('archived-checksum')
    checksum = hashlib.new(expected.attrib['style'])
    stream.seek(offset)
    assert stream.read(2) == b'\x1f\x8b', 'Expected gzip payload'
    stream.seek(offset)
    with (destination.parent/(destination.name+'-cpio.log')).open('wb') as log:
        cpio = subprocess.Popen(['cpio', '-idm', '--no-absolute-filenames', '--no-preserve-owner', '--quiet'],
            cwd=destination, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=log)
        gzip = subprocess.Popen(['gzip', '-dc'], stdin=subprocess.PIPE, stdout=cpio.stdin, stderr=log)
        cpio.stdin.close()
        try:
            while remaining:
                chunk = stream.read(min(1024*1024, remaining))
                if not chunk:
                    raise ValueError('Truncated package payload')
                checksum.update(chunk)
                gzip.stdin.write(chunk)
                remaining -= len(chunk)
            gzip.stdin.close()
            if gzip.wait() != 0 or cpio.wait() != 0:
                raise RuntimeError('Payload extraction failed; see CPIO log')
        except BaseException:
            gzip.kill()
            cpio.kill()
            gzip.wait()
            cpio.wait()
            raise
    if checksum.hexdigest() != expected.text:
        raise ValueError('Package payload checksum mismatch')
    report = {'source': str(source), 'payload_checksum_algorithm': expected.attrib['style'],
        'payload_checksum': checksum.hexdigest(), 'checksum_verified': True}
    (destination.parent/(destination.name+'-extraction.json')).write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)
