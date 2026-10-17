#!/usr/bin/env python3
"""Keep Darling's advertised plist and sysctl product versions consistent.

This is compatibility configuration, not evidence that all macOS APIs exist.
The Apple Xcode installation is untouched. Original Darling files are backed up.
"""
import json
from pathlib import Path
import plistlib

project = Path(__file__).resolve().parent.parent
guest = project / 'runtime/rootfs/usr/libexec/darling'
backup_dir = project / 'runtime/compat-backups'
backup_dir.mkdir(exist_ok=True)
kernel = guest / 'usr/lib/system/libsystem_kernel.dylib'
backup = backup_dir / 'libsystem_kernel.dylib'
if not backup.exists():
    backup.write_bytes(kernel.read_bytes())
data = backup.read_bytes()
old, new = b'11.7.4\0', b'26.2\0\0\0'
assert len(old) == len(new) and data.count(old) == 2
kernel.write_bytes(data.replace(old, new))
plist_path = Path('System/Library/CoreServices/SystemVersion.plist')
source = guest / plist_path
backup = backup_dir / 'SystemVersion.plist'
if not backup.exists():
    backup.write_bytes(source.read_bytes())
info = plistlib.loads(backup.read_bytes())
info['ProductVersion'] = info['ProductUserVisibleVersion'] = '26.2'
target = project / 'runtime/state/prefix' / plist_path
target.parent.mkdir(parents=True, exist_ok=True)
target.write_bytes(plistlib.dumps(info))
(project / 'artifacts/platform-compatibility.json').write_text(json.dumps({
    'reported_product_version': '26.2',
    'original_product_version': '11.7.4',
    'interfaces': ['SystemVersion.plist', 'sysctl kern.osproductversion'],
    'note': 'Version gates only. Does not establish implementation of macOS 26 APIs.',
    'apple_binaries_modified': False,
}, indent=2) + '\n')
print('Configured matching product-version reports in the isolated Darling runtime.')
