#!/usr/bin/env python3
"""Recreate explicitly pinned identifier constants, never provider APIs."""
from pathlib import Path
import hashlib
import json
import math
import re
import runpy
import struct
import subprocess

root = Path(__file__).resolve().parent.parent
config = json.loads((root / 'config/native-string-constants.json').read_text())
ns = runpy.run_path(str(root / 'scripts/dsc-image.py'), init_globals={
    'REFERENCE_CACHE_PATH': root / 'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT': root / 'runtime/fullsystem-libraries'})
cf = '/System/Library/Frameworks/CoreFoundation.framework/Versions/A/CoreFoundation'
isa = ns['resolve'](cf, '___CFConstantStringClassReference')
build = root / 'runtime/native-string-constants'; build.mkdir(exist_ok=True)
definitions = []; cases = []; seen = set(); hashes = {}
def checked_provider(record):
    canonical = ns['image'](record['provider']).path
    if canonical not in hashes:
        hashes[canonical] = hashlib.sha256((root / 'runtime/fullsystem-libraries' / canonical.lstrip('/')).read_bytes()).hexdigest()
    if hashes[canonical] != record['provider_sha256']:
        raise ValueError('Changed original provider: ' + record['provider'])

def checked_name(name):
    if name in seen or not re.fullmatch('_[A-Za-z_][A-Za-z0-9_]*', name):
        raise ValueError('Duplicate or invalid C symbol: ' + name)
    seen.add(name)

for record in config['constants']:
    name, provider, value = record['symbol'], record['provider'], record['value']
    checked_name(name)
    if not value or any(ord(c) < 32 or ord(c) > 126 for c in value):
        raise ValueError('Only explicit printable ASCII identifiers are supported')
    checked_provider(record)
    slot = ns['resolve'](provider, name); obj = ns['pointer'](slot)
    flags, = struct.unpack('<Q', ns['read'](obj + 8, 8))
    length, = struct.unpack('<Q', ns['read'](obj + 24, 8))
    if ns['pointer'](obj) != isa or flags != int(record['object_flags'], 0) or flags & 255 != 0xc8:
        raise ValueError('Not the pinned constant CFString: ' + name)
    if length != len(value) or ns['read'](ns['pointer'](obj + 16), length) != value.encode('ascii'):
        raise ValueError('Changed identifier value: ' + name)
    definitions.append('const void * const ' + name[1:] + ' = __builtin___CFStringMakeConstantString(' + json.dumps(value) + ');')
    cases.append('{' + json.dumps(name[1:]) + ', ' + json.dumps(value) + '}')
extra_cases = []
for record in config.get('extra_identifiers', []):
    name, provider, kind = record['symbol'], record['provider'], record['kind']
    checked_name(name); checked_provider(record)
    slot = ns['resolve'](provider, name)
    if kind == 'cstring':
        value = record['value']
        if not value or any(ord(c) < 32 or ord(c) > 126 for c in value):
            raise ValueError('Invalid C-string identifier')
        if ns['read'](ns['pointer'](slot), len(value) + 1) != value.encode('ascii') + b'\0':
            raise ValueError('Changed original C string')
        definitions.append('const char * const ' + name[1:] + ' = ' + json.dumps(value) + ';')
        extra_cases.append('{' + json.dumps(name[1:]) + ', 1, ' + json.dumps(value) + ', 0}')
    elif kind == 'uint32':
        payload = bytes.fromhex(record['bytes'])
        if len(payload) != 4 or ns['read'](slot, 4) != payload:
            raise ValueError('Changed original 32-bit identifier')
        value, = struct.unpack('<I', payload)
        definitions.append('const unsigned int ' + name[1:] + ' = ' + str(value) + 'U;')
        extra_cases.append('{' + json.dumps(name[1:]) + ', 2, 0, ' + str(value) + 'U}')
    elif kind == 'int32':
        payload = bytes.fromhex(record['bytes'])
        if len(payload) != 4 or ns['read'](slot, 4) != payload:
            raise ValueError('Changed original signed 32-bit identifier')
        value, = struct.unpack('<i', payload)
        bits, = struct.unpack('<I', payload)
        definitions.append('const int ' + name[1:] + ' = ' + str(value) + ';')
        extra_cases.append('{' + json.dumps(name[1:]) + ', 5, 0, ' + str(bits) + 'U}')
    elif kind == 'self_pointer_token':
        if ns['pointer'](slot) != slot:
            raise ValueError('Original token does not point to its own exported storage')
        definitions.append('const void * const ' + name[1:] + ' = &' + name[1:] + ';')
        extra_cases.append('{' + json.dumps(name[1:]) + ', 3, 0, 0}')
    elif kind == 'double':
        payload = bytes.fromhex(record['bytes'])
        if len(payload) != 8 or ns['read'](slot, 8) != payload:
            raise ValueError('Changed original 64-bit floating identifier')
        value, = struct.unpack('<d', payload)
        if not math.isfinite(value):raise ValueError('Unsupported non-finite floating identifier')
        definitions.append('const double ' + name[1:] + ' = ' + value.hex() + ';')
        bits, = struct.unpack('<Q', payload)
        extra_cases.append('{' + json.dumps(name[1:]) + ', 4, 0, 0, ' + hex(bits) + 'ULL}')
    else:
        raise ValueError('Unsupported identifier layout')
(build / 'constants.c').write_text('// Generated from verified original CFString objects.\n' + '\n'.join(definitions) + '\n')
(build / 'cases.h').write_text('static const struct { const char *symbol, *value; } cases[] = {\n' + ',\n'.join(cases) + '\n};\n')
with (build / 'cases.h').open('a') as out:
    out.write('static const struct { const char *symbol; int kind; const char *string; unsigned int number; unsigned long long bits; } extra_cases[] = {\n' + ',\n'.join(extra_cases) + '\n};\n')
subprocess.run(['clang-19', '-target', 'x86_64-apple-macos11', '-O2', '-c', str(build / 'constants.c'), '-o', str(build / 'constants.o')], check=True)
destination = root / 'runtime/native-library-stage/libDarlingNativeConstants.dylib'
temporary = destination.with_name(destination.name + '.pending')
subprocess.run(['ld64.lld-19', '-dylib', '-arch', 'x86_64', '-platform_version', 'macos', '11', '11',
                '-syslibroot', str(root / 'runtime/rootfs/usr/libexec/darling'), '-lSystem',
                '-framework', 'CoreFoundation', '-install_name', '/usr/lib/libDarlingNativeConstants.dylib',
                str(build / 'constants.o'), '-o', str(temporary)], check=True)
subprocess.run(['llvm-nm-19', '--defined-only', str(temporary)], check=True, stdout=(build / 'symbols.log').open('w'))
temporary.replace(destination)
print('Verified and staged ' + str(len(cases)) + ' original CFStrings and ' + str(len(extra_cases)) + ' extra identifier constants; no provider operations implemented.')
