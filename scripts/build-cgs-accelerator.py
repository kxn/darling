#!/usr/bin/env python3
"""Incrementally compile the Darling source query; build a separate unit variant."""
from pathlib import Path
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
c=json.loads((root/'config/cgs-accelerator.json').read_text())
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
repo=root/'vendor/darling/src/external/cocotron'
if subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()!=c['source_commit']:
    raise ValueError('Changed Darling source base')
if digest(root/c['backend'])!=c['backend_sha256']:raise ValueError('Changed CoreGraphics backend')
n=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={
    'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
for provider,expected,functions in [(c['actual_provider'],c['actual_provider_sha256'],c['functions']),
        (c['core_display_reference']['provider'],c['core_display_reference']['provider_sha256'],c['core_display_reference']['functions'])]:
    if digest(root/'runtime/fullsystem-libraries'/provider.lstrip('/'))!=expected:
        raise ValueError('Changed native reference image')
    for f in functions:
        if hashlib.sha256(n['read'](int(f['address'],0),f['length'])).hexdigest()!=f['sha256']:
            raise ValueError('Changed original query/ownership reference code')
if n['resolve'](c['provider'],c['import_symbol'])!=int(c['functions'][0]['address'],0):
    raise ValueError('Changed native CoreGraphics/SkyLight forwarding')
build=root/'runtime/cgs-accelerator';build.mkdir(exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
guest=root/'runtime/rootfs/usr/libexec/darling';source=root/c['source']
objects={}
for kind in ['production','unit']:
    obj=build/(kind+'.o');objects[kind]=obj
    command=['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2']
    if kind=='unit':
        command+=['-DCGDisplayIOServicePort=fixture_display',
                  '-DIOAccelFindAccelerator=fixture_accelerator','-DIOObjectRelease=fixture_release']
    subprocess.run(command+['-c',str(source),'-o',str(obj)],check=True)
output=build/'libDarlingCGSAcceleratorUnit.dylib';temporary=output.with_name(output.name+'.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11',
    '-syslibroot',str(guest),'-lSystem','-undefined','dynamic_lookup',
    '-install_name','/usr/lib/libDarlingCGSAcceleratorUnit.dylib',str(objects['unit']),'-o',str(temporary)],check=True)
temporary.replace(output)
(root/'artifacts/cgs-accelerator.json').write_text(json.dumps(dict(installed=False,
    full_compatibility=False,source_sha256=digest(source),object_sha256=digest(objects['production']),
    unit_object_sha256=digest(objects['unit']),unit_library_sha256=digest(output),
    selected_backend_ownership_execution_verified=False,real_accelerator_execution_verified=False,
    scope=c['scope'],native_cached_output_semantics=c['native_cached_output_semantics']),indent=2)+'\n')
print('Built actual Darling CoreGraphics source component and separate controlled-backend test variant')
