#!/usr/bin/env python3
"""Prepare pinned Apple slice utilities without unrelated dyld allocator code."""
from pathlib import Path
import hashlib,json,re,subprocess
root=Path(__file__).resolve().parent.parent
repo=root/'vendor/apple-dyld';config=json.loads((root/'config/dyld-cache-introspection.json').read_text())
if subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()!=config['source_commit']:
    raise ValueError('Changed Apple dyld revision')
def function(relative,pattern):
    source=(repo/relative).read_text();match=re.search(pattern,source,re.M)
    if not match:raise ValueError('Missing pinned function: '+pattern)
    opening=source.index('{',match.end());depth=1;end=opening+1
    while depth:
        depth+=(source[end]=='{')-(source[end]=='}');end+=1
    return source[match.start():end]
functions=[]
for name in ['hasMachOMagic','uses16KPages','arch','isDSYM','isObjectFile','isMachO']:
    functions.append(function('mach_o/UnsafeHeader.cpp',r'^(?:bool|Architecture|const UnsafeHeader\*) UnsafeHeader::'+name+r'\(',))
header_methods='\n\n'.join(functions)
api_functions=[function('libdyld/utils.cpp',r'^int '+name+r'\(')
    for name in ['macho_for_each_slice','macho_for_each_slice_in_fd']]
original_functions=list(api_functions)
# The pinned Apple source leaks its mapping on the malformed-fat early return.
# A stack guard keeps all parse results/callbacks while closing every mapping.
api_functions[1]=api_functions[1].replace('    int result = 0;',
    '    struct Mapping { const void* data; size_t length; ~Mapping() { ::munmap((void*)data, length); } };\n'
    '    Mapping lifetime{mappedFile, (size_t)statbuf.st_size};\n    int result = 0;',1)
api_functions[1]=api_functions[1].replace('    ::munmap((void*)mappedFile, (size_t)statbuf.st_size);\n','')
api_functions[1]=api_functions[1].replace('        bool stop;', '        bool stop = false;')
build=root/'runtime/macho-slices-source';build.mkdir(exist_ok=True)
universal=(repo/'mach_o/Universal.cpp').read_text()
# FAT32's historical extra arm64 descriptor can produce one additional slice.
# Reserve that slot in validation and honor an already requested early stop.
universal=universal.replace('sliceRanges[kMaxSliceCount]', 'sliceRanges[kMaxSliceCount + 1]')
universal=universal.replace('archsBuffer[kMaxSliceCount]', 'archsBuffer[kMaxSliceCount + 1]')
universal=universal.replace('if ( arch == Architecture::arm64 ) {', 'if ( !stop && arch == Architecture::arm64 ) {')
(build/'Universal-fixed.cpp').write_text(universal)
(build/'UnsafeHeader-selected.cpp').write_text(
    '// Selected unmodified methods from pinned Apple UnsafeHeader.cpp.\n'
    '#include "UnsafeHeader.h"\n#include "Misc.h"\nnamespace mach_o {\n'+header_methods+'\n}\n')
(build/'slice-api.cpp').write_text(
    '// Pinned Apple libdyld/utils.cpp slice APIs, with mapping lifetime cleanup.\n'
    '#include <errno.h>\n#include <unistd.h>\n#include <fcntl.h>\n#include <sys/stat.h>\n'
    '#include <sys/mman.h>\n#include <mach-o/utils.h>\n#include "Universal.h"\n'
    'using mach_o::Universal; using mach_o::UnsafeHeader; using mach_o::Error;\n'
    +'\n\n'.join('extern "C" __attribute__((visibility("default")))\n'+s for s in api_functions)+'\n')
report=dict(source_commit=config['source_commit'],runtime_execution_verified=False,
    selected_unmodified_header_methods=6,selected_api_functions=2,
    original_api_sha256=[hashlib.sha256(s.encode()).hexdigest() for s in original_functions],
    generated_files={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [build/'UnsafeHeader-selected.cpp',build/'slice-api.cpp',build/'Universal-fixed.cpp']},
    mapping_cleanup_fix=True,thin_stop_initialized=True,legacy_extra_arm64_validation_slot_and_early_stop_fixed=True,
    full_macho_validation_claimed=False)
(root/'artifacts/macho-slices-source.json').write_text(json.dumps(report,indent=2)+'\n')
