#!/usr/bin/env python3
"""Compile Apple's actual session/PSK value classes as an isolated adapter."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

project=Path(__file__).resolve().parent.parent
config=json.loads((project/'config/security-session-values.json').read_text())
repo=project/'vendor/apple-security'
if subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()!=config['source_commit']:
    raise ValueError('Changed Apple Security source revision')
sources={}
for path,digest in config['source_files'].items():
    payload=subprocess.check_output(['git','-C',str(repo),'show','HEAD:'+path])
    if hashlib.sha256(payload).hexdigest()!=digest:raise ValueError('Changed Apple source: '+path)
    sources[path]=payload.decode()
native=project/'runtime/fullsystem-libraries'/config['native_path'].lstrip('/')
if hashlib.sha256(native.read_bytes()).hexdigest()!=config['native_sha256']:
    raise ValueError('Changed native layout reference')
build=project/'runtime/security-session-values';build.mkdir(exist_ok=True)
headers=[];bodies=[]
implementation=sources['protocol/SecProtocol.m']
for name in config['classes']:
    declarations=[]
    for text in sources.values():
        declarations+=re.findall(r'@interface '+re.escape(name)+r'\b.*?@end',text,re.S)
    if len(declarations)!=1:raise ValueError('Ambiguous class declaration: '+name)
    definitions=re.findall(r'@implementation '+re.escape(name)+r'\b.*?@end',implementation,re.S)
    if len(definitions)!=1:raise ValueError('Ambiguous class implementation: '+name)
    headers+=declarations;bodies+=definitions
header=build/'classes.h';header.write_text('#import <Foundation/Foundation.h>\nNS_ASSUME_NONNULL_BEGIN\n'+ '\n\n'.join(headers)+'\nNS_ASSUME_NONNULL_END\n')
source=build/'classes.m';source.write_text('// Extracted without body changes from Apple Security '+config['source_commit']+'\n#include "classes.h"\n'+'\n\n'.join(bodies)+'\n')
checks=[]
for name,layout in config['classes'].items():
    for field in layout['ivars'] or [{'name':None,'offset':0}]:
        checks.append('{'+json.dumps(name)+','+str(layout['instance_size'])+','+
                      (json.dumps(field['name']) if field['name'] else 'NULL')+','+str(field['offset'])+'}')
(build/'native-layouts.h').write_text('static const struct { const char *name; size_t size; const char *ivar; size_t offset; } layouts[]={\n'+',\n'.join(checks)+'\n};\n')
sdk=project/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
obj=build/'classes.o'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),
    '-fobjc-arc','-O2','-c',str(source),'-o',str(obj)],check=True)
guest=project/'runtime/rootfs/usr/libexec/darling'
output=project/'runtime/native-library-stage/libDarlingSecuritySessionValues.dylib'
temporary=output.with_name(output.name+'.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11',
    '-syslibroot',str(guest),'-L',str(project/'runtime/native-library-stage'),
    '-L',str(guest/'usr/lib'),'-framework','Foundation','-lobjc','-lSystem',
    '-install_name','/usr/lib/libDarlingSecuritySessionValues.dylib',str(obj),'-o',str(temporary)],check=True)
temporary.replace(output)
report={'installed':False,'execution_verified':False,'full_compatibility':False,
    'library_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
    'source_commit':config['source_commit'],'source_files':config['source_files'],
    'classes':config['classes'],'scope':config['scope']}
(project/'artifacts/security-session-values.json').write_text(json.dumps(report,indent=2)+'\n')
print('Compiled unmodified Apple session/PSK value class bodies')
