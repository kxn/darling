#!/usr/bin/env python3
"""Stage the original mdns/PacketFilter images and an isolated Developer view."""
from pathlib import Path
import fcntl,hashlib,json,os,runpy,shutil,struct
root=Path(__file__).resolve().parent.parent
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
build=root/'runtime/mdns-native';build.mkdir(exist_ok=True)
images=[];links={}
additional=json.loads((root/'artifacts/storage-kit-dependency-candidates.json').read_text())
additional_selections=[]
for name,entry in additional.items():
    filename=Path(entry['path']).name
    destination=('frameworks/'+filename+'.framework/Versions/A/'+filename) if '.framework/' in entry['path'] else ('libraries/'+filename)
    additional_selections.append((name,filename,destination))
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    for name,filename,destination in [('mdns-native','libmdns.dylib','libraries/libmdns.dylib'),('packet-filter-native','PacketFilter','frameworks/PacketFilter.framework/Versions/A/PacketFilter'),('remote-xpc-native','RemoteXPC','frameworks/RemoteXPC.framework/Versions/A/RemoteXPC'),('rsd-full-native','RemoteServiceDiscovery','frameworks/RemoteServiceDiscovery.framework/Versions/A/RemoteServiceDiscovery'),('storage-kit-native','StorageKit','frameworks/StorageKit.framework/Versions/A/StorageKit'),('app-server-support-native','AppServerSupport','frameworks/AppServerSupport.framework/Versions/A/AppServerSupport'),*additional_selections]:
        source='runtime/rebuilt-'+name+'/'+filename
        report='runtime/rebuilt-'+name+'/reconstruction.json';data=json.loads((root/report).read_text())
        assert digest(source)==data['staged_image_sha256']
        assert not data['redirected_imports'] and not data['backend_call_overrides']
        target=build/destination;target.parent.mkdir(parents=True,exist_ok=True)
        pending=target.with_suffix('.pending');shutil.copyfile(root/source,pending);pending.replace(target)
        images.append(dict(name=name,source=source,source_sha256=digest(source),library=str(target.relative_to(root)),library_sha256=digest(str(target.relative_to(root))),reconstruction=report,reconstruction_sha256=digest(report)))
    for name in ['PacketFilter','RemoteXPC','RemoteServiceDiscovery','StorageKit','AppServerSupport',*[filename for _,filename,destination in additional_selections if destination.startswith('frameworks/')]]:
        framework=build/('frameworks/'+name+'.framework')
        for target,value in [(framework/'Versions/Current','A'),(framework/name,'Versions/Current/'+name)]:
            if not target.is_symlink():target.symlink_to(value)
    overlay=build/'Developer';(overlay/'PrivateFrameworks').mkdir(parents=True,exist_ok=True)
    # Keep existing Darling tools alongside the genuine package contents.
    packaged=root/'runtime/rootfs/usr/libexec/darling/Library/Developer'
    payload=root/'runtime/xcode-system-resources/Library/Developer'
    for relative in ['', 'PrivateFrameworks']:
        choices={child.name:'/Volumes/SystemRoot/usr/libexec/darling/Library/Developer/'+str(child.relative_to(packaged)) for child in (packaged/relative).iterdir() if child.name!='PrivateFrameworks'}
        choices.update({child.name:'/Volumes/SystemRoot/workspace/'+str(child.relative_to(root)) for child in (payload/relative).iterdir() if child.name!='PrivateFrameworks'})
        for name,value in choices.items():
            target=overlay/relative/name
            if target.is_symlink():assert os.readlink(target)==value
            else:assert not target.exists();target.symlink_to(value,target_is_directory=True)
            links[str(target.relative_to(root))]=value
record={'images':images,'developer_overlay':str(overlay.relative_to(root)),'overlay_links':links,'prefix_links_published':False,'original_package_stage':'artifacts/xcode-system-resources-stage.json','original_package_stage_sha256':digest('artifacts/xcode-system-resources-stage.json'),'runtime_execution_verified':False,'full_xcode_build_ready':False}
ns=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h','REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
key='_kSecUseSystemKeychainAlways';slot=ns['resolve']('/System/Library/Frameworks/Security.framework/Versions/A/Security',key);obj=ns['pointer'](slot)
length=struct.unpack('<Q',ns['read'](obj+24,8))[0];value=ns['read'](ns['pointer'](obj+16),length).decode('ascii');assert value=='u_SystemKeychainAlways'
base='runtime/security-policy-source/frameworks/Security.framework/Versions/A/Security';provider='runtime/state/prefix/usr/lib/libDarlingDER.dylib'
payload,changes=runpy.run_path(str(root/'scripts/macho-named-reexport.py'))['add']((root/base).read_bytes(),'/usr/lib/libDarlingDER.dylib',[key])
values=json.loads((root/'artifacts/security-out-of-band-values-build.json').read_text())
assert digest(values['library'])==values['library_sha256']
value_library=build/'libraries/libDarlingSecurityOutOfBandValues.dylib'
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);pending=value_library.with_suffix('.pending');shutil.copyfile(root/values['library'],pending);pending.replace(value_library)
payload,value_changes=runpy.run_path(str(root/'scripts/macho-named-reexport.py'))['add'](payload,'/usr/lib/libDarlingSecurityOutOfBandValues.dylib',values['exports'])
destination=build/'frameworks/Security.framework/Versions/A/Security';destination.parent.mkdir(parents=True,exist_ok=True)
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);pending=destination.with_suffix('.pending');pending.write_bytes(payload);pending.replace(destination)
    framework=build/'frameworks/Security.framework'
    for target,value_link in [(framework/'Versions/Current','A'),(framework/'Security','Versions/Current/Security')]:
        if not target.is_symlink():target.symlink_to(value_link)
record['security_identifier']={'base':base,'base_sha256':digest(base),'library':str(destination.relative_to(root)),'library_sha256':digest(str(destination.relative_to(root))),'provider':provider,'provider_sha256':digest(provider),'source':'scripts/security-constants-compat.c','source_sha256':digest('scripts/security-constants-compat.c'),'symbol':key,'value':value,'original_global':hex(slot),'export_changes':changes,'keychain_option_enforcement_verified':False}
record['security_value_classes']={'build':values,'library':str(value_library.relative_to(root)),'library_sha256':digest(str(value_library.relative_to(root))),'export_changes':value_changes}
mobile=root/'runtime/xcode-mobile-device'
record['mobile_device']={'package':'runtime/xcode-extract/Xcode.app/Contents/Resources/Packages/MobileDevice.pkg','package_sha256':digest('runtime/xcode-extract/Xcode.app/Contents/Resources/Packages/MobileDevice.pkg'),'payload_root':str(mobile.relative_to(root)),'install_location':'/Library/Apple','package_info':'runtime/xcode-mobile-device-PackageInfo.xml','package_info_sha256':digest('runtime/xcode-mobile-device-PackageInfo.xml'),'files':{str(path.relative_to(root)):digest(str(path.relative_to(root))) for path in sorted(mobile.rglob('*')) if path.is_file() and not path.is_symlink()},'symlinks':{str(path.relative_to(root)):os.readlink(path) for path in sorted(mobile.rglob('*')) if path.is_symlink()},'kernel_extensions_loaded':False,'package_scripts_executed':False}
(root/'artifacts/mdns-native-stage.json').write_text(json.dumps(record,indent=2)+'\n')
print('Staged',len(images),'original images and a private Developer view; no prefix installed')
