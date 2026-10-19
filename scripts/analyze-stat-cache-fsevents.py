#!/usr/bin/env python3
"""Audit the exact original Intel consumer without modifying its code."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,subprocess
root=Path(__file__).resolve().parent.parent
name='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang-stat-cache'
binary=root/name
before=hashlib.sha256(binary.read_bytes()).hexdigest()
symbols=subprocess.check_output(['llvm-nm-19','--arch=x86_64','--undefined-only',str(binary)],text=True)
imports=sorted(set(re.findall(r'^(_FSEvent\w+)$',symbols,re.M)))
assert imports==['_FSEventStreamCreate','_FSEventStreamSetDispatchQueue','_FSEventStreamStart','_FSEventsGetCurrentEventId']
disassembly=subprocess.check_output(['llvm-objdump-19','--macho','--arch=x86_64','--disassemble',str(binary)],text=True)
lines=disassembly.splitlines();excerpt=[]
index=next(i for i,line in enumerate(lines) if line.startswith('__ZL16FSEventsCallback') and line.endswith(':'))
callback=[]
for line in lines[index:]:
    if callback and line.endswith(':') and not re.match(r'^[0-9a-f]+:',line):break
    callback.append(line)
text='\n'.join(callback)
assert 'testb\t$0x10' in text and 'movb\t$0x1, (%rsi)' in text
assert 'symbol stub for: _CFRunLoopStop' in text and 'symbol stub for: _CFRunLoopGetCurrent' in text
for i,line in enumerate(lines):
    if 'symbol stub for: _FSEventStreamCreate' in line:excerpt.extend(lines[i-10:i+20])
excerpt+=callback
code='\n'.join(excerpt)+'\n'
assert 'symbol stub for: _FSEventsGetCurrentEventId' in code
assert 'symbol stub for: _FSEventStreamSetDispatchQueue' in code
assert 'symbol stub for: _FSEventStreamStart' in code
assert 'symbol stub for: _CFRunLoopRun' in code
log='logs/stat-cache-fsevents-consumer-disassembly.log';(root/log).write_text(code)
assert hashlib.sha256(binary.read_bytes()).hexdigest()==before
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),original_consumer=name,original_consumer_sha256=before,
    original_binary_unchanged=True,architecture='x86_64',native_FSEvents_imports=imports,
    callback_history_done_flag_test=16,callback_marks_other_events_as_changes=True,
    native_main_dispatch_queue_and_CFRunLoopRun_wait_verified=True,
    native_history_done_stops_current_CFRunLoop_verified=True,
    disassembly=log,disassembly_sha256=hashlib.sha256(code.encode()).hexdigest(),
    primary_reference='https://lists.llvm.org/pipermail/cfe-commits/Week-of-Mon-20230116/456171.html',
    reference_scope='Historical LLVM implementation explains the protocol; the exact current Intel consumer is independently checked above.',
    next_required_module='A real shared event source and global IDs; recursive monitoring and explicit unavailable-history replay must not be mistaken for that module.',
    global_ids_implemented=False,original_stat_cache_execution_succeeded=False)
(root/'artifacts/stat-cache-fsevents-consumer-audit.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
