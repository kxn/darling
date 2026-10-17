#!/usr/bin/env python3
"""Probe original LoggingSupport in a separate, coherent six-source runtime."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,shutil,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--native-quartzcore',action='store_true')
parser.add_argument('--source-dyld',action='store_true',help='Select the complete source libdyld variant with the pinned dyld2 loader')
parser.add_argument('--source-mobileasset',action='store_true',help='Select the complete source MobileAsset framework with the verified Pallas XPC client')
parser.add_argument('--native-systeminfo',action='store_true',help='Select the restored original Intel AppleSystemInfo framework and bundle resources')
parser.add_argument('--source-security-policy',action='store_true',help='Select the genuine Security base with the source optional-expiry policy component')
parser.add_argument('--pthread-yield-export',action='store_true',help='Expose the existing real pthread yield helper through the isolated libSystem copy')
args=parser.parse_args()
if args.source_dyld and not args.native_quartzcore:parser.error('--source-dyld requires --native-quartzcore')
if args.source_mobileasset and not args.source_dyld:parser.error('--source-mobileasset requires --source-dyld')
if args.native_systeminfo and not args.source_mobileasset:parser.error('--native-systeminfo requires --source-mobileasset')
if args.source_security_policy and not args.native_systeminfo:parser.error('--source-security-policy requires --native-systeminfo')
if args.pthread_yield_export and not args.source_security_policy:parser.error('--pthread-yield-export requires --source-security-policy')
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
build=root/'runtime/rebuilt-logging-support-native';source=build/'LoggingSupport'
reconstruction=json.loads((build/'reconstruction.json').read_text())
assert digest(source)==reconstruction['staged_image_sha256']
pins=json.loads((root/'config/cache-image-pins.json').read_text())['logging-support-native']
assert digest(root/'runtime/fullsystem-libraries'/pins['path'].lstrip('/'))==pins['sha256']
assert reconstruction['objc_metadata']['classes'] and len(reconstruction['objc_metadata']['classes'])==78
stage=root/'runtime/logging-support-native/frameworks'
framework=stage/'LoggingSupport.framework';destination=framework/'Versions/A/LoggingSupport'
destination.parent.mkdir(parents=True,exist_ok=True)
pending=destination.with_name('LoggingSupport.pending');shutil.copyfile(source,pending);pending.replace(destination)
for link,value in [(framework/'Versions/Current','A'),(framework/'LoggingSupport','Versions/Current/LoggingSupport')]:
    if not link.is_symlink():link.symlink_to(value)
quartzcore=None
if args.native_quartzcore:
    quartz_config=json.loads((root/'config/quartzcore-native-experiment.json').read_text())
    quartz_build=root/'runtime/rebuilt-quartzcore-native'
    quartz_report=json.loads((quartz_build/'reconstruction.json').read_text())
    quartz_pins=json.loads((root/'config/cache-image-pins.json').read_text())['quartzcore-native']
    assert digest(quartz_build/'QuartzCore')==quartz_report['staged_image_sha256']
    assert digest(root/'runtime/fullsystem-libraries'/quartz_pins['path'].lstrip('/'))==quartz_pins['sha256']
    assert len(quartz_report['objc_metadata']['classes'])==quartz_pins['objc_classes']==145
    quartz_stage=root/quartz_config['framework_stage']
    quartz_framework=quartz_stage/'QuartzCore.framework'
    quartz_destination=quartz_framework/'Versions/A/QuartzCore'
    quartz_destination.parent.mkdir(parents=True,exist_ok=True)
    pending=quartz_destination.with_name('QuartzCore.pending')
    shutil.copyfile(quartz_build/'QuartzCore',pending);pending.replace(quartz_destination)
    for link,value in [(quartz_framework/'Versions/Current','A'),(quartz_framework/'QuartzCore','Versions/Current/QuartzCore')]:
        if not link.is_symlink():link.symlink_to(value)
    quartzcore=dict(staged_framework=str(quartz_destination.relative_to(root)),
        staged_framework_sha256=digest(quartz_destination),original_framework=quartz_pins,
        reconstruction_report=str((quartz_build/'reconstruction.json').relative_to(root)),
        reconstruction_report_sha256=digest(quartz_build/'reconstruction.json'),
        restored_original_objc_classes=145,framework_execution_verified=False)
    dependency_images={}
    for entry in quartz_config['dependency_targets']:
        target=entry['target'];dependency_build=root/('runtime/rebuilt-'+target)
        dependency_pins=json.loads((root/'config/cache-image-pins.json').read_text())[target]
        name=Path(dependency_pins['path']).name
        dependency_report=json.loads((dependency_build/'reconstruction.json').read_text())
        assert digest(dependency_build/name)==dependency_report['staged_image_sha256']
        assert digest(root/'runtime/fullsystem-libraries'/dependency_pins['path'].lstrip('/'))==dependency_pins['sha256']
        assert len(dependency_report.get('objc_metadata',{}).get('classes',[]))==dependency_pins['objc_classes']
        if name.endswith('.dylib'):
            dependency_destination=root/quartz_config['library_stage']/name
        else:
            dependency_framework=quartz_stage/(name+'.framework')
            dependency_destination=dependency_framework/'Versions/A'/name
        dependency_destination.parent.mkdir(parents=True,exist_ok=True)
        pending=dependency_destination.with_name(name+'.pending')
        shutil.copyfile(dependency_build/name,pending);pending.replace(dependency_destination)
        if not name.endswith('.dylib'):
            for link,value in [(dependency_framework/'Versions/Current','A'),(dependency_framework/name,'Versions/Current/'+name)]:
                if not link.is_symlink():link.symlink_to(value)
        dependency_images[target]=dict(staged_path=str(dependency_destination.relative_to(root)),
            staged_sha256=digest(dependency_destination),original_image=dependency_pins,
            swift_relative=entry.get('swift_relative',False),execution_verified=False,
            reconstruction_report=str((dependency_build/'reconstruction.json').relative_to(root)),
            reconstruction_report_sha256=digest(dependency_build/'reconstruction.json'))
    quartzcore['dependency_images']=dependency_images
    constants_report_path=root/'artifacts/quartzcore-native-constants.json'
    constants_report=json.loads(constants_report_path.read_text())
    assert digest(root/constants_report['helper'])==constants_report['helper_sha256']
    assert constants_report['legacy_and_original_foundation_type_value_independent_copy_verified']
    quartzcore['constants_compatibility']=dict(path=str(constants_report_path.relative_to(root)),
        report_sha256=digest(constants_report_path),helper=constants_report['helper'],
        helper_sha256=constants_report['helper_sha256'],
        verified_cfstring_count=constants_report['verified_cfstring_count'],
        verified_extra_identifier_count=constants_report['verified_extra_identifier_count'])
environment=os.environ.copy();selected={}
for variable,relative in [('LINUXCODE_DARLING_SERVER','runtime/darlingserver-source-build/darlingserver/darlingserver'),
        ('LINUXCODE_LIBXPC','runtime/libxpc-source/libxpc.dylib'),('LINUXCODE_LAUNCHD','runtime/launchd-source/launchd'),
        ('LINUXCODE_LIBSYSTEM_KERNEL','runtime/libsystem-kernel-source/libsystem_kernel.dylib'),
        ('LINUXCODE_QUARANTINE','runtime/quarantine-source/libquarantine.dylib'),
        ('LINUXCODE_SANDBOX','runtime/sandbox-source/libsystem_sandbox.dylib')]:
    environment[variable]=str(root/relative);selected[variable]=dict(path=relative,sha256=digest(root/relative))
if args.source_dyld:
    relative='runtime/libdyld-source/libdyld.dylib';variable='LINUXCODE_LIBDYLD'
    environment[variable]=str(root/relative);selected[variable]=dict(path=relative,sha256=digest(root/relative))
guest='/Volumes/SystemRoot/workspace/'
frameworks=guest+str(stage.relative_to(root))+':'+guest+'runtime/foundation-native-framework-stage:'+guest+'runtime/native-framework-stage'
if quartzcore:frameworks=guest+str(quartz_stage.relative_to(root))+':'+frameworks
mobileasset=None
if args.source_mobileasset:
    mobileasset=json.loads((root/'artifacts/mobileasset-source.json').read_text())
    execution=json.loads((root/'artifacts/mobileasset-pallas-source.json').read_text())
    assert mobileasset['runtime_execution_verified'] and execution['actual_named_xpc_transport_verified']
    assert execution['legacy_and_original_foundation_verified']
    assert digest(root/mobileasset['framework'])==mobileasset['framework_sha256']==execution['framework_sha256']
    for path,value in mobileasset['source_files'].items():assert digest(root/path)==value
    assert execution['selected_runtime']==selected
    for path,value in execution['logs'].items():assert digest(root/path)==value
    frameworks=guest+'runtime/mobileasset-source/frameworks:'+frameworks
systeminfo=None
if args.native_systeminfo:
    systeminfo=json.loads((root/'artifacts/apple-system-info-native-stage.json').read_text())
    verified=json.loads((root/'artifacts/apple-system-info-native-execution.json').read_text())
    assert verified['native_execution_verified'] and verified['exit_status']==0
    assert digest(root/systeminfo['framework'])==systeminfo['framework_sha256']==verified['stage']['framework_sha256']
    assert verified['selected_runtime']==selected
    for path,value in systeminfo['staged_resources'].items():assert digest(root/path)==value
    assert digest(root/verified['log'])==verified['log_sha256']
    assert digest(root/'fixtures/hello/apple-system-info-native.m')==verified['test_source_sha256']
    assert digest(root/'artifacts/apple-system-info-native')==verified['test_binary_sha256']
    frameworks=guest+'runtime/apple-system-info-native/frameworks:'+frameworks
libraries=guest+'runtime/foundation-native-library-stage:'+guest+'runtime/native-library-stage:'+guest+'runtime/rebuilt-der:/usr/lib/swift'
if quartzcore:libraries=guest+quartz_config['library_stage']+':'+libraries
security_policy=None
if args.source_security_policy:
    security_policy=json.loads((root/'artifacts/security-policy-source.json').read_text())
    verified=json.loads((root/'artifacts/security-policy-source-execution.json').read_text())
    assert verified['runtime_execution_verified'] and verified['full_typed_option_schema_true_false_verified']
    assert verified['actual_policy_factory_and_trust_container_integration_verified']
    assert verified['selected_runtime']==selected
    assert digest(root/security_policy['staged_framework'])==security_policy['staged_framework_sha256']==verified['staged_framework_sha256']
    assert digest(root/security_policy['library'])==security_policy['library_sha256']==verified['library_sha256']
    for path,value in security_policy['source_files'].items():assert digest(root/path)==value
    for path,value in verified['logs'].items():assert digest(root/path)==value
    frameworks=guest+'runtime/security-policy-source/frameworks:'+frameworks
    libraries=guest+'runtime/security-policy-source/libraries:'+libraries
yield_export=None
if args.pthread_yield_export:
    yield_export=json.loads((root/'artifacts/pthread-yield-export-stage.json').read_text())
    execution=json.loads((root/'artifacts/pthread-yield-export-execution.json').read_text())
    assert execution['runtime_execution_verified'] and execution['exact_main_thread_Linux_sched_yield_syscalls_between_markers']==256
    assert execution['selected_runtime']==selected and execution['stage']==yield_export
    assert digest(root/yield_export['staged_library'])==yield_export['staged_library_sha256']
    assert digest(root/yield_export['base'])==yield_export['base_sha256']
    assert digest(root/yield_export['provider'])==yield_export['provider_sha256']
    for path,value in execution['logs'].items():assert digest(root/path)==value
    libraries=guest+'runtime/pthread-yield-export/libraries:'+libraries
command=['timeout','-k','5','60','bin/darling','shell','/usr/bin/env','OBJC_DISABLE_TAGGED_POINTERS=YES',
    'DYLD_FRAMEWORK_PATH='+frameworks,'DYLD_LIBRARY_PATH='+libraries,'/usr/bin/xcodebuild','-showsdks']
log=root/('logs/xcode-pthread-yield-export-showsdks.log' if args.pthread_yield_export else 'logs/xcode-source-security-policy-showsdks.log' if args.source_security_policy else 'logs/xcode-native-apple-system-info-showsdks.log' if args.native_systeminfo else 'logs/xcode-source-mobileasset-showsdks.log' if args.source_mobileasset else 'logs/xcode-native-quartzcore-source-dyld-showsdks.log' if args.source_dyld else 'logs/xcode-native-quartzcore-showsdks.log' if quartzcore else 'logs/xcode-native-logging-support-showsdks.log')
with log.open('w') as stream:
    result=subprocess.run(command,cwd=root,env=environment,stdout=stream,stderr=subprocess.STDOUT)
original=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
assert digest(original)==digest(root/'runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),installed=False,
    full_compatibility=False,framework_execution_verified=False,
    original_framework=pins,restored_original_objc_classes=78,source_private_class_replacement_added=False,
    staged_framework=str(destination.relative_to(root)),staged_framework_sha256=digest(destination),
    reconstruction_report=str((build/'reconstruction.json').relative_to(root)),
    reconstruction_report_sha256=digest(build/'reconstruction.json'),
    source_runtime=selected,original_xcodebuild_sha256=digest(original),command=command,
    native_quartzcore=quartzcore,
    source_mobileasset=mobileasset,
    native_systeminfo=systeminfo,
    source_security_policy=security_policy,
    pthread_yield_export=yield_export,
    exit_status=result.returncode,sdk_listing_succeeded=result.returncode==0,
    log=str(log.relative_to(root)),log_sha256=digest(log),diagnostic=log.read_text(),
    full_xcode_build_ready=False,signing_ready=False)
(root/('artifacts/pthread-yield-export-xcode-probe.json' if args.pthread_yield_export else 'artifacts/security-policy-source-xcode-probe.json' if args.source_security_policy else 'artifacts/apple-system-info-native-xcode-probe.json' if args.native_systeminfo else 'artifacts/mobileasset-source-xcode-probe.json' if args.source_mobileasset else 'artifacts/quartzcore-native-source-dyld-probe.json' if args.source_dyld else 'artifacts/quartzcore-native-probe.json' if quartzcore else 'artifacts/logging-support-native-probe.json')).write_text(json.dumps(report,indent=2)+'\n')
print('Original Xcode with isolated native frameworks:',result.returncode)
raise SystemExit(0 if result.returncode==0 else 1)
