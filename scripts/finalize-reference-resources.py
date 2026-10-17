#!/usr/bin/env python3
"""Restore selected payload hard links and record the extracted resource bytes.

The resource data came from Apple's full installer, decoded by its aa utility
under Darling. No ownership, flags, timestamps or code signatures are applied.
"""
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import plistlib
import zipfile

project=Path(__file__).resolve().parent.parent
config=json.loads((project/'config/apple-installer-25G83.json').read_text())
archive=next((project/'runtime/fullsystem/sharedsupport').rglob(config['mobileasset_zip_name']))
with archive.open('rb') as stream:
    if hashlib.file_digest(stream,'sha256').hexdigest()!=config['mobileasset_zip_sha256']:
        raise ValueError('Reference asset ZIP SHA256 mismatch')
stage=project/'runtime/fullsystem/framework-resources'
prefixes=[
    'System/Library/PrivateFrameworks/CoreEmoji.framework/Versions/A/Resources/',
    'System/Library/Frameworks/NaturalLanguage.framework/Versions/A/Resources/',
    'System/Library/PrivateFrameworks/LinguisticData.framework/Versions/A/Resources/',
]
def selected(path):return any(path.startswith(prefix) for prefix in prefixes)
auxiliary_sources={
    'System/Library/Audio/Tunings/AID25/ADM/config.plist',
    'System/Library/LinguisticData/RequiredAssets_ar.bundle/version.plist',
}
def safe_path(path):
    parts=PurePosixPath(path)
    if parts.is_absolute() or '..' in parts.parts:raise ValueError('Unsafe archive link path')
    result=stage/path
    if not result.resolve().is_relative_to(stage.resolve()):raise ValueError('Archive link escapes stage')
    return result
with zipfile.ZipFile(archive) as source:
    lines=source.read('AssetData/payloadv2/links.txt').decode().splitlines()
links=[];current=None
for line in lines:
    if line.startswith('='):current=line[1:]
    elif line.startswith('+'):
        destination=line[1:]
        if selected(destination):
            if current is None or not (selected(current) or current in auxiliary_sources):
                raise ValueError('Resource link source was not selected: '+str(current))
            links.append((current,destination))
    else:raise ValueError('Unknown payload links record')
for source_name,destination_name in links:
    source,destination=safe_path(source_name),safe_path(destination_name)
    if not source.is_file():raise ValueError('Missing hard-link source: '+source_name)
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():
        if destination.read_bytes()!=source.read_bytes():raise ValueError('Conflicting resource hard link')
    else:os.link(source,destination)
records=[];plists=0
for prefix in prefixes:
    root=safe_path(prefix)
    for path in sorted(root.rglob('*')):
        if not path.is_file():continue
        data=path.read_bytes()
        if path.suffix=='.plist':plistlib.loads(data);plists+=1
        records.append({'path':str(path.relative_to(stage)),'length':len(data),
            'sha256':hashlib.sha256(data).hexdigest()})
report={'source_asset_sha256':config['mobileasset_zip_sha256'],
    'source_asset_sha256_verified':True,'source_build':config['build'],
    'restored_hard_links':len(links),'validated_plists':plists,'files':records,
    'scope':'Resource bytes only. Original aa convert/extract omits ownership, modes, flags and times. No bundle signature or complete OS validation.'}
(project/'artifacts/framework-reference-resources.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'Restored {len(links)} resource hard links, validated {plists} plists; recorded {len(records)} resource files.')
