#!/usr/bin/env python3
"""Compare declared old/new objc layouts and prove the upstream ISA storage port."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, subprocess

root = Path(__file__).resolve().parent.parent
repo = root / 'vendor/darling/src/external/objc4'
modern = root / 'vendor/apple-objc4'
runtime = repo / 'runtime'
build = root / 'runtime/objc-source'
reference = build / 'original-layout-reference'
reference.mkdir(exist_ok=True)
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
commit = subprocess.check_output(['git', '-C', str(modern), 'rev-parse', 'HEAD'], text=True).strip()
assert commit == 'fb265098298302243cd7eeaa1f63f0ba7786dd9a'
modern_text = (modern / 'runtime/objc-private.h').read_text()
text = (runtime / 'objc-private.h').read_text()
for line in ['char isa_storage[sizeof(isa_t)];', 'isa_t &isa() { return *reinterpret_cast<isa_t *>(isa_storage); }',
    'const isa_t &isa() const { return *reinterpret_cast<const isa_t *>(isa_storage); }']:
    assert line in text and line in modern_text
roots = []
for name in ['objc-private.h', 'objc-object.h']:
    payload = subprocess.check_output(['git', '-C', str(repo), 'show', 'HEAD:runtime/' + name])
    path = reference / name
    path.write_bytes(payload)
    roots.append({'type': 'file', 'name': str(runtime / name), 'external-contents': str(path)})
overlay = reference / 'overlay.json'
overlay.write_text(json.dumps({'version': 0, 'use-external-names': False, 'roots': roots}, indent=2))
probe = build / 'layout-probe.mm'
probe.write_text('''#include "objc-private.h"
extern "C" const unsigned long linuxcode_objc_layout[] = {
sizeof(objc_object), alignof(objc_object), sizeof(isa_t), alignof(isa_t),
sizeof(objc_class), alignof(objc_class), __builtin_offsetof(objc_class,superclass),
__builtin_offsetof(objc_class,cache), __builtin_offsetof(objc_class,bits)};
''')
command = json.loads((build / '8-objc-class.inputs.json').read_text())['command']
command = command[:command.index('-MD')]
results = {}
for label in ['original', 'source']:
    output = build / ('layout-' + label + '.ll')
    args = command + (['-ivfsoverlay', str(overlay)] if label == 'original' else [])
    subprocess.run(args + ['-S', '-emit-llvm', str(probe), '-o', str(output)], check=True)
    line = next(line for line in output.read_text().splitlines() if line.startswith('@linuxcode_objc_layout ='))
    values = [int(value) for value in re.findall(r'i64 (\d+)', line)]
    assert len(values) == 9, line
    results[label] = values
assert results['original'][0] == results['source'][0] == 8
assert results['original'][1] == 8 and results['source'][1] == 1
assert results['original'][2:] == results['source'][2:]
report = dict(checked_at=datetime.now(timezone.utc).isoformat(),
    fields=['object_size', 'object_cpp_alignment', 'isa_size', 'isa_alignment', 'class_size', 'class_alignment',
        'superclass_offset', 'cache_offset', 'bits_offset'], layouts=results,
    object_word_and_class_ABI_preserved=True, Cpp_object_alignment_reduced_to_support_LSB_tags=True,
    upstream_storage_and_accessor_lines_unchanged=True, upstream_commit=commit,
    upstream_url='https://github.com/apple-oss-distributions/objc4/blob/' + commit + '/runtime/objc-private.h',
    source_files={str(p.relative_to(root)): digest(p) for p in [runtime / 'objc-private.h', runtime / 'objc-object.h',
        runtime / 'NSObject.mm', modern / 'runtime/objc-private.h']},
    compiler_outputs={str(p.relative_to(root)): digest(p) for p in [build / 'layout-original.ll', build / 'layout-source.ll']},
    scope='Declared and compiler-emitted Intel C++ ABI comparison. Runtime behavior is validated separately; no ARM execution claim.')
(root / 'artifacts/objc-source-layout-analysis.json').write_text(json.dumps(report, indent=2) + '\n')
print('Compared original/source layouts:', results)
