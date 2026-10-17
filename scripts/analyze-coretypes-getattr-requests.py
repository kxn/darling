#!/usr/bin/env python3
"""Decode genuine Foundation getattrlist requests captured by the live debugger."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re
root=Path(__file__).resolve().parent.parent
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
header='vendor/darling/src/external/xnu/bsd/sys/attr.h'
generic='vendor/darling/src/external/xnu/darling/src/libsystem_kernel/emulation/include/xnu_syscall/bsd/helper/xattr/getattrlist_generic.c'
definitions=re.findall(r'^#define\s+(\w+)\s+(0x[0-9A-Fa-f]+)\b',(root/header).read_text(),re.M)
def names(value,prefix):
    found={}
    for name,number in definitions:
        bit=int(number,16)
        if name.startswith(prefix) and bit and bit&(bit-1)==0 and bit&value:found.setdefault(bit,name)
    return [found[b] for b in sorted(found)]
raw=(root/'logs/coretypes-getattr-gdb.log').read_text();lines=raw.splitlines();requests=[]
for i,line in enumerate(lines):
    match=re.fullmatch(r'METADATA_AT size=(\d+) options=(0x[0-9a-f]+)',line)
    if not match:continue
    words=[]
    for row in lines[i+1:i+3]:words.extend(int(n,16) for n in re.findall(r'0x[0-9a-f]+',row.split(':',1)[1]))
    assert len(words)==6 and words[0]==5
    _,common,volume,directory,file,fork=words;options=int(match[2],16)
    # These are the actual current supported masks, not a new implementation.
    text=(root/generic).read_text()
    for declaration in ['#define COMMON_SUPPORTED (ATTR_CMN_FNDRINFO | ATTR_CMN_OBJTAG)',
        '#define DIR_SUPPORTED (ATTR_DIR_ENTRYCOUNT)', '#define FILE_SUPPORTED (ATTR_FILE_RSRCLENGTH)', '#define FORK_SUPPORTED 0']:
        assert declaration in text
    unsupported=dict(common=common&~0x4010,volume=volume,directory=directory&~2,file=file&~0x1000,fork=fork)
    requests.append(dict(size=int(match[1]),options=hex(options),option_names=names(options,'FSOPT_'),
        path=lines[i+3].split(':',1)[1].strip(),raw_masks=[hex(v) for v in words[1:]],
        common=names(common,'ATTR_CMN_'),directory=names(directory,'ATTR_DIR_'),file=names(file,'ATTR_FILE_'),
        extended_common=names(fork,'ATTR_CMNEXT_') if options&0x20 else [],
        unsupported_by_current_backend={k:hex(v) for k,v in unsupported.items() if v},
        rejected_by_current_supported_mask_checks=any(unsupported.values())))
assert len(requests)==4 and all(r['rejected_by_current_supported_mask_checks'] for r in requests)
assert requests[0]['raw_masks']==['0xd01f9e0d','0x0','0x5','0x1','0x240'] and requests[0]['options']=='0x25'
observed=json.loads((root/'artifacts/coretypes-resource-values-debug.json').read_text())
assert observed['exit_status']==1 and not observed['Foundation_URL_and_enumeration_verified']
assert digest(observed['log'])==observed['log_sha256']
assert digest('fixtures/hello/coretypes-resource-values.m')==observed['source_sha256']
assert digest('artifacts/coretypes-resource-values')==observed['binary_sha256']
paths=[header,generic,'logs/coretypes-getattr-gdb.log','logs/coretypes-getattr-live-maps.log','runtime/coretypes-getattr.gdb','artifacts/coretypes-resource-values-debug.json']
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),requests=requests,evidence={p:digest(p) for p in paths},
    original_Foundation_metadata_requests_observed=True,source_mask_rejection_explains_EINVAL=True,
    backend_modified=False,metadata_fixed=False,
    scope='Actual CoreTypes URL/NSFileManager reproducer in the selected source runtime. This does not assert every original lsd metadata request has been observed or that all required metadata is implemented.',
    next_implementation='Implement real stat-backed metadata, returned attribute sets, extended-common selection, Darwin attribute packing/reference offsets and bounded copies in the shared source kernel path. Preserve unsupported/invalid errors. Test all path/FD entry points and genuine Foundation/LaunchServices use; do not hard-code CoreTypes values or merely advertise unsupported fields.')
(root/'artifacts/coretypes-getattr-request-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
for request in requests:print(request['options'],request['raw_masks'],request['common'],request['extended_common'])
print('All four genuine requests are rejected by existing supported-mask checks; no kernel implementation changed')
