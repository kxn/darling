#!/usr/bin/env python3
"""Rebuild/publish the separate original Foundation experiment; never install."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess

project=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--stage-only',action='store_true')
args=parser.parse_args()
config=json.loads((project/'config/foundation-native-experiment.json').read_text())
pins=json.loads((project/'config/cache-image-pins.json').read_text())
if not args.stage_only:
    subprocess.run(['python3',str(project/'scripts/build-xpc-rich-error.py')],cwd=project,check=True)
    subprocess.run(['python3',str(project/'scripts/build-security-session-values.py')],cwd=project,check=True)
    subprocess.run(['python3',str(project/'scripts/build-native-string-constants.py')],cwd=project,check=True)
    subprocess.run(['python3',str(project/'scripts/build-objc-class-enumeration.py')],cwd=project,check=True)
    subprocess.run(['python3',str(project/'scripts/build-openat-dprotected.py')],cwd=project,check=True)
    subprocess.run(['python3',str(project/'scripts/build-foundation-libc-compat.py')],cwd=project,check=True)
    subprocess.run(['python3',str(project/'scripts/build-legacy-foundation-exports.py')],cwd=project,check=True)
helper=project/'runtime/native-library-stage/libDarlingXPCRichError.dylib'
helper_report=json.loads((project/'artifacts/xpc-rich-error-compat.json').read_text())
if hashlib.sha256(helper.read_bytes()).hexdigest()!=helper_report['library_sha256']:
    raise ValueError('Rich-error helper differs from its build report')
session=project/'runtime/native-library-stage/libDarlingSecuritySessionValues.dylib'
session_report=json.loads((project/'artifacts/security-session-values.json').read_text())
if hashlib.sha256(session.read_bytes()).hexdigest()!=session_report['library_sha256']:
    raise ValueError('Session value helper differs from its build report')
enumeration=project/'runtime/native-library-stage/libDarlingObjCEnumeration.dylib'
enum_report=json.loads((project/'artifacts/objc-class-enumeration.json').read_text())
if hashlib.sha256(enumeration.read_bytes()).hexdigest()!=enum_report['library_sha256']:
    raise ValueError('Class enumeration helper differs from its build report')
openat=project/'runtime/native-library-stage/libDarlingOpenAt.dylib'
openat_report=json.loads((project/'artifacts/openat-dprotected.json').read_text())
if hashlib.sha256(openat.read_bytes()).hexdigest()!=openat_report['library_sha256']:
    raise ValueError('Protected-open helper differs from its build report')
libc=project/'runtime/native-library-stage/libDarlingFoundationSystem.dylib'
libc_report=json.loads((project/'artifacts/foundation-libc-compat.json').read_text())
if hashlib.sha256(libc.read_bytes()).hexdigest()!=libc_report['library_sha256']:
    raise ValueError('Foundation libc helper differs from its build report')
legacy=project/'runtime/native-library-stage/libDarlingLegacyFoundation.dylib'
legacy_report=json.loads((project/'artifacts/legacy-foundation-exports.json').read_text())
if hashlib.sha256(legacy.read_bytes()).hexdigest()!=legacy_report['library_sha256']:
    raise ValueError('Legacy private Foundation helper differs from its build report')
for entry in config['targets']:
    target=entry['target']
    if not args.stage_only:
        command=['python3',str(project/'scripts/rebuild-c-cache-image.py'),
                 '--target',target,'--modern-adapter','--lazy-functions']
        if entry.get('swift_relative'):
            command+=['--experimental-swift','--repair-swift-relative']
        with (project/'logs'/('rebuild-'+target+'-experimental.log')).open('w') as log:
            subprocess.run(command,cwd=project,stdout=log,stderr=subprocess.STDOUT,check=True)
    name=Path(pins[target]['path']).name
    source=project/('runtime/rebuilt-'+target)/name
    report=json.loads((source.parent/'reconstruction.json').read_text())
    if hashlib.sha256(source.read_bytes()).hexdigest()!=report['staged_image_sha256']:
        raise ValueError('Image differs from reconstruction: '+target)
    if name.endswith('.dylib'):
        stage_name=entry.get('stage_name',name)
        if Path(stage_name).name!=stage_name or not stage_name.endswith('.dylib'):
            raise ValueError('Invalid standalone library stage name')
        destination=project/config['library_stage']/stage_name
    else:
        version='C' if name=='Foundation' else 'A'
        bundle=project/config['framework_stage']/(name+'.framework')
        destination=bundle/'Versions'/version/name
        destination.parent.mkdir(parents=True,exist_ok=True)
        for link,value in [(bundle/'Versions/Current',version),
                           (bundle/name,'Versions/Current/'+name)]:
            if link.is_symlink() and link.readlink()==Path(value):continue
            if link.exists() and not link.is_symlink():
                raise ValueError('Unexpected existing framework path: '+str(link))
            temporary=link.with_name(link.name+'.pending')
            if temporary.is_symlink():temporary.unlink()
            temporary.symlink_to(value);temporary.replace(link)
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=destination.with_name(destination.name+'.pending')
    shutil.copyfile(source,temporary);shutil.copymode(source,temporary)
    temporary.replace(destination)
    print(target,report['staged_image_sha256'],flush=True)
# Existing Darling support libraries name libFND directly. Route that name to
# this experiment's actual Foundation, so the old class implementations are
# never deliberately added alongside the native classes by this dependency.
facade=project/config['library_stage']/'libFND.dylib'
temporary=facade.with_name(facade.name+'.pending')
command=['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11',
         '-syslibroot',str(project/'runtime/rootfs/usr/libexec/darling'),
         '-L',str(project/'runtime/native-library-stage'),
         '-L',str(project/'runtime/rootfs/usr/libexec/darling/usr/lib'),
         '-install_name','/usr/lib/libFND.dylib','-reexport_library',
         str(project/config['framework_stage']/'Foundation.framework/Foundation'),
         '-lSystem','-o',str(temporary)]
subprocess.run(command,cwd=project,check=True)
temporary.replace(facade)
# Modern macOS exposes this API family through Network.framework. Heimdal in
# the old backend names libnetwork instead. Reexport the same actual image so
# its opaque objects and Objective-C classes have a single implementation.
network=project/config['library_stage']/'libnetwork.dylib'
temporary=network.with_name(network.name+'.pending')
command=['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11',
         '-syslibroot',str(project/'runtime/rootfs/usr/libexec/darling'),
         '-L',str(project/'runtime/native-library-stage'),
         '-L',str(project/'runtime/rootfs/usr/libexec/darling/usr/lib'),
         '-install_name','/usr/lib/libnetwork.dylib','-reexport_library',
         str(project/config['framework_stage']/'Network.framework/Network'),
         '-lSystem','-o',str(temporary)]
subprocess.run(command,cwd=project,check=True)
temporary.replace(network)
# C helpers built against Darling's original CF library must use the same
# actual CoreFoundation as the native framework, including its class objects.
corefoundation=project/config['library_stage']/'libCF.dylib'
temporary=corefoundation.with_name(corefoundation.name+'.pending')
command=['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11',
         '-syslibroot',str(project/'runtime/rootfs/usr/libexec/darling'),
         '-L',str(project/'runtime/native-library-stage'),
         '-L',str(project/'runtime/rootfs/usr/libexec/darling/usr/lib'),
         '-install_name','/usr/lib/libCF.dylib','-reexport_library',
         str(project/config['framework_stage']/'CoreFoundation.framework/CoreFoundation'),
         '-lSystem','-o',str(temporary)]
subprocess.run(command,cwd=project,check=True)
temporary.replace(corefoundation)
