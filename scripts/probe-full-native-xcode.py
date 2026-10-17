#!/usr/bin/env python3
"""Verify staged component identity and run original Xcode SDK enumeration.

A successful SDK listing does not establish project builds or signing.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,subprocess
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-runtime',action='store_true',help='Use the independently built darlingserver and complete libxpc')
parser.add_argument('--source-kernel',action='store_true',help='Also use the complete source libsystem_kernel; requires --source-runtime')
parser.add_argument('--source-quarantine',action='store_true',help='Also use source responsibility APIs; requires --source-kernel')
parser.add_argument('--source-sandbox',action='store_true',help='Also use source sandbox syscall wrappers; requires --source-quarantine')
args=parser.parse_args()
if args.source_kernel and not args.source_runtime:parser.error('--source-kernel requires --source-runtime')
if args.source_quarantine and not args.source_kernel:parser.error('--source-quarantine requires --source-kernel')
if args.source_sandbox and not args.source_quarantine:parser.error('--source-sandbox requires --source-quarantine')
root=Path(__file__).resolve().parent.parent
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
config=json.loads((root/'config/foundation-native-experiment.json').read_text())
pins=json.loads((root/'config/cache-image-pins.json').read_text())
images={}
for entry in config['targets']:
    target=entry['target'];name=Path(pins[target]['path']).name
    reconstruction=json.loads((root/('runtime/rebuilt-'+target)/'reconstruction.json').read_text())
    stage=root/config['library_stage']/entry.get('stage_name',name) if name.endswith('.dylib') else root/config['framework_stage']/(name+'.framework')/name
    if digest(stage)!=reconstruction['staged_image_sha256']:raise ValueError('Changed native image: '+target)
    images[target]=digest(stage)
components={}
for name,config_name in [('ca-render-server','ca-render-server'),('iokit-main-port','iokit-main-port'),('cgs-accelerator','cgs-accelerator')]:
    report=json.loads((root/'artifacts'/(name+'.json')).read_text())
    for prefix in ['stage_framework','stage_backend']:
        if digest(root/report[prefix])!=report[prefix+'_sha256']:raise ValueError('Changed staged source component: '+name)
    original=json.loads((root/'config'/(config_name+'.json')).read_text())
    if digest(root/original['backend'])!=original['backend_sha256']:raise ValueError('Changed original backend: '+name)
    if name=='ca-render-server':
        if digest(root/'vendor/darling/src/external/cocotron/QuartzCore/CARenderServer.m')!=report['source_sha256']:
            raise ValueError('QuartzCore source changed after testing')
        if not report['selected_api_execution_verified']:raise ValueError('QuartzCore execution proof absent')
    elif name=='iokit-main-port':
        for filename,key in [('IOKitLib.c','source_sha256'),('IOKitLib.h','header_sha256')]:
            if digest(root/'vendor/darling/src/external/IOKitUser'/filename)!=report[key]:
                raise ValueError('IOKit source changed after staging')
    else:
        if digest(root/original['source'])!=report['source_sha256']:
            raise ValueError('CoreGraphics source changed after testing')
        if not report['selected_backend_ownership_execution_verified']:
            raise ValueError('CoreGraphics ownership proof absent')
    components[name]={k:report[k] for k in ['stage_framework','stage_framework_sha256','stage_backend','stage_backend_sha256']}
original=root/'runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
installed=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
if digest(original)!=digest(installed):raise ValueError('Original Apple xcodebuild was modified')
adapter_path=root/'runtime/native-library-stage/libDarlingXPCRichError.dylib'
adapter_report=json.loads((root/'artifacts/xpc-rich-error-compat.json').read_text())
if digest(adapter_path)!=adapter_report['library_sha256']:
    raise ValueError('Changed XPC rich-error/connection adapter')
external_components={'xpc_rich_error':dict(path=str(adapter_path.relative_to(root)),sha256=digest(adapter_path))}
guest='/Volumes/SystemRoot/workspace/'
command=['timeout','-k','5','60','bin/darling','shell','/usr/bin/env','OBJC_DISABLE_TAGGED_POINTERS=YES',
    'DYLD_FRAMEWORK_PATH='+guest+config['framework_stage']+':'+guest+'runtime/native-framework-stage',
    'DYLD_LIBRARY_PATH='+guest+config['library_stage']+':'+guest+'runtime/native-library-stage:'+guest+'runtime/rebuilt-der:/usr/lib/swift',
    '/usr/bin/xcodebuild','-showsdks']
suffix='-source-sandbox' if args.source_sandbox else '-source-responsibility' if args.source_quarantine else '-source-kernel' if args.source_kernel else '-source' if args.source_runtime else ''
log=root/('logs/xcode-full-native-foundation'+suffix+'-showsdks.log')
environment=os.environ.copy()
source_runtime={}
if args.source_runtime:
    for variable,relative in [('LINUXCODE_DARLING_SERVER','runtime/darlingserver-source-build/darlingserver/darlingserver'),
                              ('LINUXCODE_LIBXPC','runtime/libxpc-source/libxpc.dylib'),
                              ('LINUXCODE_LAUNCHD','runtime/launchd-source/launchd')]:
        path=root/relative
        source_runtime[variable]=dict(path=relative,sha256=digest(path))
        environment[variable]=str(path)
if args.source_kernel:
    relative='runtime/libsystem-kernel-source/libsystem_kernel.dylib'
    path=root/relative
    source_runtime['LINUXCODE_LIBSYSTEM_KERNEL']=dict(path=relative,sha256=digest(path))
    environment['LINUXCODE_LIBSYSTEM_KERNEL']=str(path)
if args.source_quarantine:
    relative='runtime/quarantine-source/libquarantine.dylib'
    path=root/relative
    source_runtime['LINUXCODE_QUARANTINE']=dict(path=relative,sha256=digest(path))
    environment['LINUXCODE_QUARANTINE']=str(path)
if args.source_sandbox:
    relative='runtime/sandbox-source/libsystem_sandbox.dylib'
    path=root/relative
    source_runtime['LINUXCODE_SANDBOX']=dict(path=relative,sha256=digest(path))
    environment['LINUXCODE_SANDBOX']=str(path)
for variable in ['LINUXCODE_DARLING_SERVER','LINUXCODE_LIBXPC','LINUXCODE_LAUNCHD','LINUXCODE_LIBSYSTEM_KERNEL','LINUXCODE_QUARANTINE','LINUXCODE_SANDBOX']:
    if environment.get(variable) and variable not in source_runtime:
        path=Path(environment[variable]).resolve()
        source_runtime[variable]=dict(path=str(path),sha256=digest(path),inherited=True)
with log.open('w') as stream:
    result=subprocess.run(command,cwd=root,env=environment,stdout=stream,stderr=subprocess.STDOUT)
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),installed=False,
    full_xcode_build_ready=False,signing_ready=False,probe='xcodebuild -showsdks',
    exit_status=result.returncode,sdk_listing_succeeded=result.returncode==0,
    log=str(log.relative_to(root)),latest_diagnostic=log.read_text(),command=command,
    apple_xcodebuild_sha256=digest(installed),apple_xcodebuild_matches_xip_extraction=True,
    tagged_pointer_optimization_disabled=True,native_image_count=len(images),images=images,
    source_components=components,
    external_compatibility_components=external_components,
    source_runtime=source_runtime,
    complete_libsystem_kernel_source_selected=args.source_kernel,
    source_quarantine_responsibility_selected=args.source_quarantine,
    source_sandbox_wrappers_selected=args.source_sandbox,
    implementation_form='Darling QuartzCore, IOKit and CoreGraphics source components incrementally linked with existing backends in the isolated stage; remaining compatibility work still includes external libraries and experimental Mach-O rebinding/reexports. No full Darling rebuild.')
(root/('artifacts/xcode-full-native-foundation'+suffix+'-probe.json')).write_text(json.dumps(report,indent=2)+'\n')
print('Original staged xcodebuild -showsdks exit:',result.returncode)
raise SystemExit(0 if result.returncode==0 else 1)
