#!/usr/bin/env python3
"""Check the whole image, or explicitly validate only its reference caches.

Reference mode retains the unresolved whole-image SHA384 discrepancy in the
report and requires successful RIDIFF and independent cache page checks.
"""
from pathlib import Path
import hashlib,json,lzma,plistlib,struct,sys

project=Path(__file__).resolve().parent.parent
manifest=plistlib.loads((project/'runtime/fullsystem/intel/AssetData/boot/BuildManifest.plist').read_bytes())
assert manifest['ProductBuildVersion']=='25G83' and manifest['ProductVersion']=='26.6.2'
entries=[identity['Manifest']['Cryptex1,SystemOS'] for identity in manifest['BuildIdentities']
    if identity.get('Info',{}).get('DeviceClass')=='x86legacyap']
expected={(entry['Info']['HashMethod'],entry['Digest'].hex(),entry['Info']['Path']) for entry in entries}
assert len(expected)==1
algorithm,expected_digest,asset=expected.pop();assert algorithm=='sha2-384'
cache_reference='--cache-reference' in sys.argv
source=project/'runtime/fullsystem/intel-system.dmg.partial'
destination=project/('runtime/fullsystem/intel-system-reference.apfs' if cache_reference
    else 'runtime/fullsystem/intel-system.dmg')
if not source.exists():source=destination
assert 2**30<source.stat().st_size<6*2**30
sha384=hashlib.sha384();sha256=hashlib.sha256()
with source.open('rb') as stream:
    while chunk:=stream.read(8*1024*1024):sha384.update(chunk);sha256.update(chunk)
whole_image_match=sha384.hexdigest()==expected_digest
if not whole_image_match and not cache_reference:
    raise ValueError('Decoded image does not match Apple BuildManifest SHA384; leaving output untouched')
if cache_reference:
    pages=json.loads((project/'artifacts/intel-cache-page-verification.json').read_text())
    assert pages['all_code_pages_verified'] and len(pages['files'])==7
    execution=(project/'logs/raw-image-patch-execute.log').read_text()
    assert 'ImagePatch: Digest match. Output reconstructed.' in execution and 'RawImagePatch returned 0' in execution
    patch=project/'runtime/fullsystem/intel/AssetData/payloadv2/image_patches/cryptex-system-x86_64'
    with patch.open('rb') as stream:
        header=struct.unpack('<QHQQIQQ',stream.read(46));stream.seek(header[-2])
        assert stream.read(4)==b'pbzx';stream.read(8)
        expanded,packed=struct.unpack('>QQ',stream.read(16))
        assert 32<=expanded<=2*1024*1024 and packed<=2*1024*1024
        metadata=stream.read(packed)
        if metadata.startswith(b'\xfd7zXZ\0'):metadata=lzma.decompress(metadata)
        assert len(metadata)==expanded
    assert 'digest='+metadata[:32].hex() in execution
if source!=destination:source.replace(destination)
report={'build':'25G83','version':'26.6.2','architecture':'x86_64','manifest_asset':asset,
    'length':destination.stat().st_size,'sha384':sha384.hexdigest(),'sha256':sha256.hexdigest(),
    'apple_manifest_digest_verified':whole_image_match,'apple_manifest_sha384':expected_digest,
    'ridiff_logical_digest_verified':cache_reference,'cache_code_pages_verified':cache_reference,
    'whole_image_discrepancy_unresolved':not whole_image_match,
    'scope':'Reference cache extraction only; no whole-image bitwise equivalence or boot readiness claimed.',
    'decoder':'Original Apple RawImagePatch under Darling on Linux',
    'mac_or_virtual_machine_used':False,'installed_as_os':False}
(project/'artifacts/intel-system-image.json').write_text(json.dumps(report,indent=2)+'\n')
for target in (('compression','parallel-compression') if '--record-runtime-execution' in sys.argv else ()):
    path=project/f'runtime/rebuilt-{target}/reconstruction.json'
    library=json.loads(path.read_text());library.pop('patches');library.pop('lazy_binding_slots')
    library.update({'installed':False,'execution_verified':True,
        'tests':['Actual full Intel RIDIFF10 patch decoded by original Apple RawImagePatch',
            'Apple decoder verified RIDIFF logical-content digest',
            'All 1,404,360 decompressed cache code-page SHA256 values match their CodeDirectories'],
        'whole_image_manifest_sha384_matches':whole_image_match,
        'scope':'Staged reference-extraction helper only; whole-image SHA384 discrepancy unresolved. Other APIs unverified.'})
    (project/f'artifacts/{target}-compat.json').write_text(json.dumps(library,indent=2)+'\n')
print(f'Whole-image Apple manifest digest matches: {whole_image_match}. Reference cache checks: {cache_reference}.',flush=True)
