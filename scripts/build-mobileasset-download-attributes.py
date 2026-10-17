#!/usr/bin/env python3
"""Compile the complete Darling MobileAsset source framework with Pallas client."""
from pathlib import Path
import hashlib,json,re,subprocess
root=Path(__file__).resolve().parent.parent
source=root/'vendor/darling/src/private-frameworks/MobileAsset'
build=root/'runtime/mobileasset-download-attributes';build.mkdir(exist_ok=True)
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
guest=root/'runtime/rootfs/usr/libexec/darling'
baseline=root/'runtime/mobileasset-source/frameworks/MobileAsset.framework/Versions/A/MobileAsset'
section=(source/'CMakeLists.txt').read_text().split('SOURCES',1)[1].split('DEPENDENCIES',1)[0]
sources=[source/p for p in re.findall(r'src/\S+\.m',section)];assert len(sources)==15
reference=json.loads((root/'artifacts/mobileasset-download-attributes-reference.json').read_text())
assert digest(root/reference['provider'])==reference['provider_sha256']
constants=(source/'src/ASAttributeConstants.m').read_text()
for name,item in reference['constants'].items():assert 'NSString *const '+name+' = @'+json.dumps(item['value'])+';' in constants
objects=[]
for p in sources:
    obj=build/(p.stem+'.o');objects.append(obj)
    subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),
        '-I',str(source/'include'),'-fblocks','-O2','-c',str(p),'-o',str(obj)],check=True)
framework=build/'frameworks/MobileAsset.framework';output=framework/'Versions/A/MobileAsset'
output.parent.mkdir(parents=True,exist_ok=True);pending=output.with_name('MobileAsset.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11',
    '-install_name','/System/Library/PrivateFrameworks/MobileAsset.framework/Versions/A/MobileAsset',
    '-compatibility_version','1.0.0','-current_version','1.0.0','-syslibroot',str(guest),
    '-F',str(guest/'System/Library/Frameworks'),'-lSystem','-lobjc','-framework','Foundation',
    *[str(p) for p in objects],'-o',str(pending)],check=True)
exports=lambda p:set(re.findall(r'^(?:0x[\da-fA-F]+|\[re-export\])\s+(\S+)',subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(p)],text=True),re.M))
old=exports(baseline);new=exports(pending)
assert not old-new,sorted(old-new)
assert {'_MAGetPallasEnabled','__MAsendGetPallasEnabled','_MAGetPallasAudience',
    '_MASetPallasEnabled','_MASetPallasAudienceForType','_MASetPallasUrlForType','_ASAttributeDownloadSize','_ASAttributeUnarchivedSize'}<=new
pending.replace(output)
for path,target in [(framework/'Versions/Current','A'),(framework/'MobileAsset','Versions/Current/MobileAsset')]:
    if not path.is_symlink():path.symlink_to(target)
report=dict(installed=False,full_framework_source_build=True,complete_source_files=len(sources),
    native_attribute_reference='artifacts/mobileasset-download-attributes-reference.json',native_attribute_reference_sha256=digest(root/'artifacts/mobileasset-download-attributes-reference.json'),
    source_revision=subprocess.check_output(['git','-C',str(root/'vendor/darling'),'rev-parse','HEAD'],text=True).strip(),
    source_files={str(p.relative_to(root)):digest(p) for p in [*sources,source/'CMakeLists.txt',*sorted((source/'include/MobileAsset').glob('*.h'))]},
    baseline=str(baseline.relative_to(root)),baseline_sha256=digest(baseline),
    framework=str(output.relative_to(root)),framework_sha256=digest(output),
    original_exports_preserved=len(old),source_exports=len(new),runtime_execution_verified=False,
    protocol_scope='All five DVT Pallas client operations over genuine named XPC transport, plus default audience/URL wrappers and their internal aliases. No MobileAsset daemon, catalog, download or installation implementation. Other generic framework stubs remain.',
    connection_scope='One connection/UUID per call; one retry on interruption. No persistent MAXpcManager cache or general service manager implementation.',
    known_limits=['Bootstrap preflight handles an absent service without entering the old unconnected-channel backend. A service disappearing between lookup and XPC activation remains a backend race to resolve.',
        'Other MobileAsset APIs remain legacy stubs. No real Apple daemon interoperation or end-to-end download proof.'],
    full_xcode_build_ready=False,signing_ready=False)
(root/'artifacts/mobileasset-download-attributes-build.json').write_text(json.dumps(report,indent=2)+'\n')
print('Built all 15 MobileAsset source files, preserving previous exports and adding two native-valued attribute names:',output)
