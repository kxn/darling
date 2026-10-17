#!/usr/bin/env python3
"""Guard and correct the pinned project Darling server's x86_64h CPU report.

The current server hardcodes the generic subtype in three API result stores.
Change only those three immediate bytes, only on real supported CPU/OS state.
The launch guard stays active for every later invocation of this project.
"""
from pathlib import Path
from datetime import datetime,timezone
import fcntl
import hashlib
import json
import shutil
import stat
import subprocess

root=Path(__file__).resolve().parent.parent
config=json.loads((root/'config/darling-host-cpu.json').read_text())
probe=root/'runtime/tools/check-haswell-host';temporary=probe.with_name(probe.name+'.pending')
subprocess.run(['clang-19','-O2','-march=x86-64','-mno-avx','-mno-avx2',
    str(root/'scripts/check-haswell-host.c'),'-o',str(temporary)],check=True)
temporary.replace(probe)
result=subprocess.run([str(probe),'--json'],capture_output=True,text=True,check=True)
hardware=json.loads(result.stdout)
if not hardware['haswell_isa_supported']:raise ValueError('Do not report unsupported x86_64h hardware')
source=root/config['runtime_binary'];backup=root/'runtime/compat-backups/darlingserver'
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    if backup.exists():original=backup.read_bytes()
    else:original=source.read_bytes()
    if hashlib.sha256(original).hexdigest()!=config['original_sha256']:
        raise ValueError('Unexpected original Darling server; do not patch another runtime version')
    patched=bytearray(original)
    for entry in config['patches']:
        off=int(entry['file_offset'],0);old=bytes.fromhex(entry['original_instruction']);new=bytes.fromhex(entry['patched_instruction'])
        if len(old)!=7 or old[:3] not in (b'\xc7\x40\x04',b'\xc7\x40\x10') or old[3:]!=b'\x03\0\0\0':
            raise ValueError('Patch is not the reviewed 32-bit CPU subtype immediate')
        if new[:3]!=old[:3] or new[3:]!=b'\x08\0\0\0' or patched[off:off+7]!=old:
            raise ValueError('Original CPU subtype instruction changed')
        patched[off:off+7]=new
    differences=[i for i,(a,b) in enumerate(zip(original,patched)) if a!=b]
    if differences!=sorted(int(e['file_offset'],0)+3 for e in config['patches']):
        raise ValueError('Patch modified bytes outside the three reviewed subtype constants')
    current=source.read_bytes()
    if current not in (original,bytes(patched)):raise ValueError('Current server differs from original and reviewed patched image')
    if not backup.exists():
        backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,backup);shutil.copymode(source,backup)
    if current!=patched:
        temporary=source.with_name(source.name+'.pending');temporary.write_bytes(patched)
        temporary.chmod(stat.S_IMODE(source.stat().st_mode));temporary.replace(source)
    report={'checked_at':datetime.now(timezone.utc).isoformat(),'config':config,'host_hardware':hardware,
        'patched_sha256':hashlib.sha256(patched).hexdigest(),'changed_file_byte_offsets':[hex(i) for i in differences],
        'host_kernel_modified':False,'runtime_launch_guard':str(probe.relative_to(root)),
        'execution_verified':False,'full_compatibility':False}
    marker=root/'runtime/state/host-cpu-haswell.json';temporary=marker.with_suffix('.pending')
    temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(marker)
    (root/'artifacts/host-cpu-compat.json').write_text(json.dumps(report,indent=2)+'\n')
print('Corrected three project-local subtype stores after actual CPU/OS ISA checks; launch guard enabled.')
