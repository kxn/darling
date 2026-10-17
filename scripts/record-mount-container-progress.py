#!/usr/bin/env python3
"""Record real mount-path/CM/LaunchServices progress; full Xcode remains incomplete."""

# Preserve the newer native cryptography and FileCoordination checkpoint.
from pathlib import Path as _nc_Path
import json as _nc_json
_nc_state = _nc_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _nc_state.exists() and _nc_json.loads(_nc_state.read_text()).get('primary_report') == 'artifacts/native-crypto-progress.json':
    print('Preserving the newer native cryptography checkpoint'); raise SystemExit(0)

# Historical recorders must preserve the newer archive/crypto checkpoint.
from pathlib import Path as _ac_Path
import json as _ac_json
_ac_state = _ac_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _ac_state.exists() and _ac_json.loads(_ac_state.read_text()).get('primary_report') == 'artifacts/archive-crypto-progress.json':
    print('Preserving the newer archive/crypto checkpoint'); raise SystemExit(0)

# Historical recorders must preserve the newer dispatch/XPC checkpoint.
from pathlib import Path as _dx_Path
import json as _dx_json
_dx_state = _dx_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _dx_state.exists() and _dx_json.loads(_dx_state.read_text()).get('primary_report') == 'artifacts/dispatch-xpc-progress.json':
    print('Preserving the newer dispatch/XPC checkpoint'); raise SystemExit(0)

# A historical recorder must not replace the newer active checkpoint.
from pathlib import Path as _cw_Path
import json as _cw_json
_cw_state = _cw_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _cw_state.exists() and _cw_json.loads(_cw_state.read_text()).get('primary_report') == 'artifacts/cryptex-workqueue-progress.json':
    print('Preserving the newer Cryptex/workqueue checkpoint'); raise SystemExit(0)
# A historical recorder must not replace the current validated runtime state.
from pathlib import Path as _qvf_Path
import json as _qvf_json
_qvf_state = _qvf_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _qvf_state.exists() and _qvf_json.loads(_qvf_state.read_text()).get('primary_report') in {'artifacts/quarantine-vfs-progress.json','artifacts/device-identity-progress.json'}:
    print('Preserving the newer Quarantine VFS checkpoint'); raise SystemExit(0)
# A historical recorder must not replace the current dependency/source checkpoint.
from pathlib import Path as _mdns_Path
import json as _mdns_json
_mdns_state = _mdns_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _mdns_state.exists() and _mdns_json.loads(_mdns_state.read_text()).get('primary_report') in {'artifacts/mdns-source-progress.json','artifacts/security-cloud-rpc-progress.json','artifacts/security-current-item-progress.json','artifacts/sandbox-check-progress.json','artifacts/expected-sandbox-runtime-progress.json','artifacts/coreutils-quarantine-progress.json'}:
    print('Preserving newer mdns/source checkpoint; historical recorder skipped')
    raise SystemExit(0)
# Preserve the newer source log-pack/FSEvents checkpoint when replaying an old recorder.
import json as _pack_json
from pathlib import Path as _PackPath
_pack_state = _PackPath(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _pack_state.exists() and _pack_json.loads(_pack_state.read_text()).get('primary_report') == 'artifacts/log-pack-progress.json':
    print('Preserving newer source log-pack/FSEvents checkpoint')
    raise SystemExit(0)
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') == 'artifacts/foundation-coherent-progress.json':
    print('Preserving the newer source selector/coherent Foundation/SDK checkpoint')
    raise SystemExit(0)

if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') == 'artifacts/fsevents-flush-progress.json':
    print('Preserving the newer source FSEvents flush checkpoint')
    raise SystemExit(0)

if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') == 'artifacts/combine-fsevents-progress.json':
    print('Preserving the newer original Combine/source FSEvents checkpoint')
    raise SystemExit(0)

if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') == 'artifacts/imageio-native-progress.json':
    print('Preserving the newer original ImageIO/source-ABI checkpoint')
    raise SystemExit(0)

if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') == 'artifacts/mobilegestalt-progress.json':
    print('Preserving the newer MobileGestalt/source-dyld checkpoint')
    raise SystemExit(0)

if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') in {'artifacts/layer-log-progress.json','artifacts/log-hooks-progress.json'}:
    print('Preserving the newer source layer/log checkpoint')
    raise SystemExit(0)

read=lambda p:json.loads((root/p).read_text())
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
k=runpy.run_path(str(root/'scripts/mount-path-kernel-profile.py'))['profile']()
p=runpy.run_path(str(root/'scripts/container-manager-profile.py'))['profile'](kernel_profile=k)
build=p['source_kernel'];stage=p['container_manager'];selected=p['source_runtime']
assert build['full_libsystem_kernel_source_build'] and build['complete_source_files']==875
assert not build['full_darling_rebuild'] and not build['installed']
for item in build['sources']:assert digest(item['source'])==item['sha256']
for name,sha in build['metadata_source_headers'].items():assert digest(name)==sha
for item in selected.values():assert digest(item['path'])==item['sha256']
assert stage['export_changes']['original_instructions_and_other_bytes_preserved'] and not stage['export_changes']['provider_entire_namespace_reexported']
assert len(stage['export_changes']['added_names'])==17
for key in ['base','library','original','provider','client','helper','source','trampolines']:assert digest(stage[key])==stage[key+'_sha256']
ref=read('vendor/apple-xnu-statfs-ext/reference.json')
for name,item in ref['files'].items():assert digest('vendor/apple-xnu-statfs-ext/'+name)==item['sha256']
wrapper='vendor/darling/src/external/xnu/libsyscall/wrappers/statfs_ext.c'
assert (root/wrapper).read_text().replace('#ifdef DARLING\n#include "statfs_ext_compat.h"\n#endif\n\n','')==(root/'vendor/apple-xnu-statfs-ext/libsyscall/wrappers/statfs_ext.c').read_text()
assert '\twrappers/statfs_ext.c\n' in (root/'vendor/darling/src/external/xnu/libsyscall/CMakeLists.txt').read_text()
mount=read('artifacts/mount-path-kernel-test.json');meta=read('artifacts/mount-path-metadata-kernel-test.json')
results={mode:read('artifacts/mount-path-container-manager-'+mode+'-probe.json') for mode in ['lifecycle','foundation','version','showsdks']}
lsd_path='artifacts/native-lsd-mount-path-container-manager-metadata-kernel-sysdir-paired-dirhelper-sandbox-container-datavault-user-local-dir-source-libtrace-probe.json';lsd=read(lsd_path)
for result in [mount,meta,*results.values(),lsd]:
 assert result['source_runtime']==selected and result['source_kernel']==build
 if 'log' in result:assert digest(result['log'])==result['log_sha256']
 for name,sha in result.get('logs',{}).items():assert digest(name)==sha
for mode,result in results.items():assert result['container_manager']==stage
assert mount['exit_status']==0 and mount['runtime_execution_verified']
assert not mount['host_mounts_changed'] and mount['host_mountinfo_before_sha256']==mount['host_mountinfo_after_sha256']
assert meta['exit_status']==0 and meta['runtime_execution_verified']
assert digest('fixtures/hello/mount-path-kernel.c')==mount['source_sha256'] and digest('artifacts/mount-path-kernel')==mount['binary_sha256']
assert digest('runtime/mount-fixture/session.sh')==mount['session_script_sha256']
assert digest('fixtures/hello/metadata-kernel.c')==meta['source_sha256'] and digest('artifacts/metadata-kernel')==meta['binary_sha256']
counts=re.search(r'MOUNT_PATH_KERNEL_PASS checks=(\d+) filesystems=(\d+)',mount['diagnostic']);assert counts
assert 'METADATA_KERNEL_PASS checks=11444 unique_filesystems=10' in (root/meta['log']).read_text()
for mode in ['lifecycle','foundation','version']:assert results[mode]['exit_status']==0 and results[mode]['runtime_execution_verified']
assert 'CONTAINER_API_REAL_QUERY_LOCAL_LIFETIME_256_OBJECTS_OK' in results['lifecycle']['diagnostic']
assert 'CORETYPES_METADATA_RESULT directory=1 attributes=1 enumeration=3 errors=0' in results['foundation']['diagnostic']
assert 'Xcode 26.6\nBuild version 17F113' in results['version']['diagnostic']
assert results['showsdks']['exit_status']==255 and '_OBJC_CLASS_$_CALayerContext' in results['showsdks']['diagnostic']
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
assert digest(original)==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
for result in results.values():assert result['original_xcodebuild_sha256']==digest(original)
for mode,source,binary in [('lifecycle','fixtures/hello/container-manager.c','artifacts/container-manager'),('foundation','fixtures/hello/coretypes-resource-values.m','artifacts/coretypes-resource-values')]:
 assert results[mode]['source_sha256']==digest(source) and results[mode]['binary_sha256']==digest(binary)
assert lsd['container_manager']==stage and lsd['exit_status']==0 and lsd['UTI_functional_execution_verified']
assert lsd['original_binary_sha256']==lsd['staged_binary_sha256']==digest('runtime/native-lsd/lsd')
assert len(lsd['selected_job']['MachServices'])==13
assert lsd['paired_dirhelper_job']['MachServices']=={'com.apple.bsd.dirhelper':True}
assert 'NATIVE_LSD_CLIENT_STATUS 0' in lsd['diagnostic']
for marker in ['NATIVE_UTI_URL_EXTENSION_OK '+s for s in ['public.plain-text','public.png','public.json','com.adobe.pdf']]:assert marker in lsd['diagnostic']
for name in ['public.plain-text','public.png','public.json','com.adobe.pdf']:assert 'NATIVE_UTI_CONFORMANCE_OK '+name in lsd['diagnostic']
assert 'NATIVE_UTI_TYPED_TAG_CONFORMANCE_AND_URL_EXTENSION_OK' in lsd['diagnostic']
assert 'Creating dispatch_data for XPC coder with length' in lsd['daemon_diagnostic']
assert 'Error -43 registering path /System/Library/CoreServices/CoreTypes.bundle' not in lsd['daemon_diagnostic']
assert 'Symbol not found:' not in lsd['daemon_diagnostic']
assert 'Failed to start translocation service' in lsd['daemon_diagnostic']
assert "LSD_STATFS_RESULT -2 '/state/prefix'" in (root/'logs/native-lsd-statfs-gdb.log').read_text()
xnu=root/'vendor/darling/src/external/xnu'
tracked=['darling/src/libsystem_kernel/emulation/include/xnu_syscall/bsd/helper/xattr/getattrlist_generic.c','darling/src/libsystem_kernel/emulation/include/conversion/stat/common.h','darling/src/libsystem_kernel/emulation/include/xnu_syscall/bsd/impl/xattr/getattrlistbulk.h','darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/impl/xattr/getattrlistbulk.c','darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/impl/stat/getfsstat.c','darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/impl/stat/statfs.c','darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/impl/stat/fstatfs.c','darling/src/libsystem_kernel/emulation/src/linux_premigration/vchroot_userspace.c','libsyscall/CMakeLists.txt']
added=['darling/src/libsystem_kernel/emulation/include/xnu_syscall/bsd/helper/xattr/metadata_linux.h','darling/src/libsystem_kernel/emulation/include/xnu_syscall/bsd/helper/stat/mounts.h','libsyscall/wrappers/statfs_ext.c','libsyscall/wrappers/statfs_ext_compat.h']
patch=subprocess.check_output(['git','diff','--binary','--',*tracked],cwd=xnu)
for path in added:
 assert subprocess.run(['git','ls-files','--error-unmatch',path],cwd=xnu,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
 extra=subprocess.run(['git','diff','--no-index','--binary','--','/dev/null',path],cwd=xnu,capture_output=True);assert extra.returncode==1;patch+=extra.stdout
patch_path='artifacts/darling-mount-metadata-statfs-ext.patch';pending=root/(patch_path+'.pending');pending.write_bytes(patch);pending.replace(root/patch_path)
subprocess.run(['git','apply','--reverse','--check',str(root/patch_path)],cwd=xnu,check=True)
paths=['artifacts/mount-path-kernel-source-build.json','artifacts/container-manager-export-stage.json','artifacts/mount-path-kernel-test.json','artifacts/mount-path-metadata-kernel-test.json',lsd_path]+['artifacts/mount-path-container-manager-'+m+'-probe.json' for m in results]+['vendor/apple-xnu-statfs-ext/reference.json','logs/native-lsd-statfs-gdb.log','logs/native-lsd-statfs-live-maps.log','runtime/native-lsd-statfs.gdb',patch_path]
scripts=['build-libsystem-kernel-source.py','metadata-kernel-profile.py','mount-path-kernel-profile.py','test-metadata-kernel.py','test-mount-path-kernel.py','stage-container-manager-export.py','container-manager-native-loader.c','build-container-manager-trampolines.py','container-manager-profile.py','probe-container-manager.py','probe-native-lsd.py','build-launch-debug-gate.py','launch-debug-gate.c','debug-native-lsd-statfs.py','record-mount-container-progress.py']
source={str((xnu/n).relative_to(root)):digest(str((xnu/n).relative_to(root))) for n in tracked+added}
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),previous_report='artifacts/metadata-kernel-progress.json',previous_goal_turn_classification='progress',
 evidence={n:digest(n) for n in paths},source=source,scripts={'scripts/'+n:digest('scripts/'+n) for n in scripts},selected_runtime=selected,
 source_files_compiled=875,metadata_assertions=11444,mount_path_assertions=int(counts[1]),private_mount_filesystems_observed=int(counts[2]),
 original_CM_entry_targets_verified=17,real_owned_query_objects_verified=256,Apple_statfs_ext_source_commit=ref['commit'],
 native_LaunchServices_system_job_and_complete_current_UTI_fixture_verified=True,CoreTypes_registration_ENOENT_resolved=True,
 original_xcode_version_verified=True,sdk_listing_verified=False,full_xcode_build_ready=False,signing_ready=False,installed_as_default=False,
 implementation_form='Direct Darling source mount-path translation and shared proc mount parser, statfs/fstatfs identity/name consistency, safe vchroot reverse expansion and Apple upstream statfs_ext/fstatfs_ext wrappers in the real libsyscall CMake source list. Complete 875-file kernel component rebuilt privately. Seventeen original ContainerManager entries use a deferred C resolver plus x86_64 register-preserving tail calls to the unchanged original provider; no container query result is fabricated. Original lsd and original Swift UTI client communicate with the real Mach/XPC/CSStore path. Original xcodebuild remains unchanged; runtime still combines source components and selected compatibility/reexport libraries.',
 limits=[
  'Current UTI fixture proves four identifier/preferred-extension/URL-extension cases, four conformances to data, png-extension and JSON-MIME reverse lookup with original lsd alive before and after. This is not an audit of every CoreTypes declaration or every LaunchServices service/domain.',
  'The real ContainerManager object lifecycle and entry targets are verified. The remote-placeholder query reports a real execution error and lsd continues. No functioning container manager daemon, successful protected container creation or authorization enforcement is claimed.',
  'statfs_ext uses Apple’s unchanged fallback after the older backend rejects newer volume attribute bits with EINVAL. This does not claim a filesystem-I/O-free NOBLOCK implementation. Linux mount flags/types, owner mapping, stable IDs across newly mounted overlays and all mount races still need broader Darwin fidelity work.',
  'Previous bulk limitations remain: shared-open-description locking, full PACK_INVAL_ATTRS error records and XNU NOCROSSMOUNT semantics are incomplete. Volume UUID/snapshots/ACL/added time/generation/data-protection metadata remain unsupported or unadvertised.',
  'Native lsd cannot start the translocation service; protected mkdir/policy support and root-only audit identity/version remain limited. The unchanged recovery bundle also contains an empty Contents/Library file, reported as a nonfatal not-a-directory while scanning.',
  'Default launcher remains the older baseline. Current source/runtime profile is separately selected; a clean unified full Darling build has not been produced. Genuine -showsdks still fails on CALayerContext and no complete project/build/archive/sign/export run exists.'])
destination='artifacts/mount-container-progress.json';pending=root/(destination+'.pending');pending.write_text(json.dumps(record,indent=2)+'\n');pending.replace(root/destination)
state=read('artifacts/current-work-state.json')
state.update(updated_at=record['checked_at'],primary_report=destination,goal_status='active',complete=False,active_build=dict(task='source-mount-paths-native-CM-and-running-LaunchServices',running=False,report=destination),latest_implementation_form=record['implementation_form'],latest_selected_runtime=selected,
 latest_staged_coreml_and_metal_blocker='Original lsd now stays alive and the complete current Swift UTI fixture passes identifier, preferred/URL extensions, data conformance and extension/MIME reverse lookup. CoreTypes ENOENT resolved through guest mount-name translation and source statfs_ext wrapper; 875-file source kernel, 11444 metadata assertions and 2497 real mount/API assertions pass. Genuine -version passes; -showsdks still lacks CALayerContext. Full build/archive/sign/export remain incomplete.')
remove=('Diagnose native lsd CoreTypes registration ENOENT','Restore the real container_query_create','Once original lsd starts and replies','Complete remaining metadata backend semantics when required:','Resolve the real CALayerContext dependency')
state['next_work']=list(dict.fromkeys([
 'Resolve genuine xcodebuild -showsdks loader blocker CALayerContext. Inspect Cocotron AppKit layer-context contracts against original QuartzCore and implement a real source-backed bridge or adapt AppKit to an available backend. Do not alias CAContext or provide an empty successful rendering backend.',
 'Integrate the verified mount-path kernel, CM exports and original dirhelper/lsd jobs into a reproducible private CI launcher when the remaining Xcode loader requirements are satisfied. Preserve original xcodebuild commands, project files and actual errors.',
 'Complete required metadata fidelity: shared-open-description bulk locking, full invalid-attribute error records, mount crossing semantics, actual Darwin mount flags/owner identity and stable filesystem IDs across fresh overlay mounts. The current mount round trips and original UTI client are verified; these broader properties are not.',
]+[s for s in state['next_work'] if not s.startswith(remove)]))
state['last_verification']=list(dict.fromkeys(state['last_verification']+[
 'Direct source mount-path/statfs_ext fixes and 17 genuine CM entries allow original lsd to remain alive while the complete current Swift UTI fixture passes all four URL/type cases, data conformances and png/JSON tag reverse lookups. Complete 875-file kernel build passes 11444 metadata assertions and 2497 assertions using actual bind/tmpfs mounts, escaped names, prefix collisions, deleted FDs and Apple statfs_ext fallback/error rules. Genuine -version passes; -showsdks remains CALayerContext failure. Full Xcode goal is incomplete.']))
state['latest_validation_reports']=list(dict.fromkeys(state['latest_validation_reports']+paths+[destination]))
state.setdefault('source_components',{}).update(metadata_kernel='artifacts/mount-path-kernel-source-build.json',mount_path_kernel='artifacts/mount-path-kernel-source-build.json',native_container_manager='artifacts/container-manager-export-stage.json',mount_container_progress=destination)
pending=root/'artifacts/current-work-state.json.pending';pending.write_text(json.dumps(state,indent=2)+'\n');pending.replace(root/'artifacts/current-work-state.json')
print('Recorded running original lsd and passing complete current UTI fixture; full Xcode goal remains active')
