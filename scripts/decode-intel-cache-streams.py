#!/usr/bin/env python3
"""Decode selected APFS resource forks using the pinned native Linux codec."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import subprocess

project=Path(__file__).resolve().parent.parent
revision=subprocess.check_output(['git','-C',str(project/'vendor/libzbitmap'),'rev-parse','HEAD'],text=True).strip()
assert revision=='574abeae25b25c3319b9b6a9225cc7464e08ae88'
subprocess.run(['clang-19','-O3','-fno-strict-aliasing','-I',str(project/'vendor/libzbitmap'),
    str(project/'scripts/decode-apfs-zbm.c'),str(project/'vendor/libzbitmap/libzbitmap.c'),
    '-o',str(project/'runtime/tools/decode-apfs-zbm')],check=True)
source=project/'runtime/fullsystem/intel-cache-streams/System/Library/dyld'
destination=project/'runtime/fullsystem/intel-cache';destination.mkdir(parents=True,exist_ok=True)
names=['dyld_shared_cache_x86_64h']+[f'dyld_shared_cache_x86_64h.{i:02d}' for i in range(1,7)]
def decode(name):
    output=destination/(name+'.partial')
    with (project/f'logs/decode-{name}.log').open('wb') as log:
        subprocess.run([str(project/'runtime/tools/decode-apfs-zbm'),
            str(source/(name+':com.apple.decmpfs')),str(source/(name+':com.apple.ResourceFork')),
            str(output)],stdout=log,stderr=subprocess.STDOUT,check=True)
    with output.open('rb') as stream:
        if not stream.read(16).startswith(b'dyld_v1'):raise ValueError('Decoded file is not a dyld cache')
    output.replace(destination/name)
    return name
with ThreadPoolExecutor(max_workers=2) as pool:
    for future in as_completed([pool.submit(decode,name) for name in names]):
        print('Decoded '+future.result(),flush=True)
