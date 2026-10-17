#!/usr/bin/env python3
"""Validate real-image table analysis and rejection of a damaged table entry."""
from pathlib import Path
import hashlib
import json
import re
import runpy
import struct

project=Path(__file__).resolve().parent.parent
build=project/'runtime/rebuilt-coreml'
expected=json.loads((build/'code-analysis.json').read_text())
config=json.loads((project/'config/cache-image-pins.json').read_text())['coreml']
source=project/'runtime/fullsystem-libraries'/config['path'].lstrip('/')
assert hashlib.sha256(source.read_bytes()).hexdigest()==config['sha256']
ns=runpy.run_path(str(project/'scripts/dsc-image.py'),init_globals={
    'REFERENCE_CACHE_PATH':project/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT':project/'runtime/fullsystem-libraries'})
analysis=runpy.run_path(str(project/'scripts/cache-code-analysis.py'))
data=(build/'CoreML.analysis-only.macho').read_bytes()
cursor=32
for _ in range(struct.unpack_from('<I',data,16)[0]):
    command,size=struct.unpack_from('<II',data,cursor)
    if command==2:symoff,count,stroff,strsize=struct.unpack_from('<IIII',data,cursor+8)
    cursor+=size
functions=[struct.unpack_from('<Q',data,symoff+16*index+8)[0] for index in range(count)]
assert len(functions)==expected['function_entries'] and functions==sorted(set(functions))
disassembly=(build/'original-disassembly.log').read_text()
diagnostics={}
baseline=analysis['tail_jump_tables'](disassembly,functions,ns['read'],diagnostics)
(build/'code-analysis-diagnostics.json').write_text(json.dumps(diagnostics,indent=2)+'\n')
assert baseline==expected['tail_tables'] and len(baseline)>1
chosen=baseline[0]
damaged=struct.pack('<i',0x7fffffff)
def damaged_read(address,length):
    result=bytearray(ns['read'](address,length))
    for position in range(max(address,chosen['start']),min(address+length,chosen['start']+4)):
        result[position-address]=damaged[position-chosen['start']]
    return bytes(result)
negative=analysis['tail_jump_tables'](disassembly,functions,damaged_read)
assert negative==[table for table in baseline if table['function']!=chosen['function']]
# In this pinned, real function the table LEA is followed by MOV r13,rcx.
# Replace that MOV with MOV rax,rcx: the table base in RAX is now destroyed.
# Both are genuine three-byte instructions, so instruction boundaries remain
# unchanged. The analysis must reject the family through register provenance.
lea=0x7ff80df27228;overwrite=0x7ff80df2722f
instructions=analysis['parse_instructions'](disassembly)
assert instructions[overwrite][0]==bytes.fromhex('49 89 cd')
candidate=next(record for record in diagnostics['candidates'].values() if record['instruction']==lea)
assert any(table['function']==candidate['function'] for table in baseline)
modified,count=re.subn(r'^7ff80df2722f:.*$',
    '7ff80df2722f: 48 89 c8                movq %rcx, %rax',disassembly,flags=re.MULTILINE)
assert count==1
overwritten=analysis['tail_jump_tables'](modified,functions,ns['read'])
assert overwritten==[table for table in baseline if table['function']!=candidate['function']]
import capstone
report={
    'source_sha256':config['sha256'],'function_entries':len(functions),
    'analysis_script_sha256':hashlib.sha256((project/'scripts/cache-code-analysis.py').read_bytes()).hexdigest(),
    'verified_tables':len(baseline),'verified_entries':sum(table['entries'] for table in baseline),
    'damaged_entry_rejects_whole_function_table_family':True,
    'other_function_tables_unchanged':True,'source_image_modified':False,
    'overwritten_base_register_rejects_table_family':True,
    'capstone_distribution':json.loads((project/'config/capstone.json').read_text())['version'],
    'capstone_wheel_sha256':json.loads((project/'config/capstone.json').read_text())['sha256'],
    'capstone_binding_version':capstone.__version__,
    'scope':'Static analysis validation only; does not prove CoreML runtime compatibility.'}
(project/'artifacts/coreml-code-table-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(f"REAL_COREML_TABLE_ANALYSIS_AND_DAMAGED_ENTRY_REJECTION_OK tables={len(baseline)}")
