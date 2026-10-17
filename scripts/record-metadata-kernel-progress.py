#!/usr/bin/env python3
"""Publish source-backed metadata progress without declaring the Xcode goal complete."""

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

read=lambda s:json.loads((root/s).read_text())
digest=lambda s:hashlib.sha256((root/s).read_bytes()).hexdigest()
if read('artifacts/current-work-state.json').get('primary_report') == 'artifacts/mount-container-progress.json':
    print('Preserving newer source mount/ContainerManager checkpoint')
    raise SystemExit(0)
profile=runpy.run_path(str(root/'scripts/metadata-kernel-profile.py'))['profile']()
build=read('artifacts/metadata-kernel-source-build.json')
test=read('artifacts/metadata-kernel-test.json')
foundation=read('artifacts/metadata-kernel-foundation-probe.json')
version=read('artifacts/metadata-kernel-version-probe.json')
sdks=read('artifacts/metadata-kernel-showsdks-probe.json')
lsd_path='artifacts/native-lsd-metadata-kernel-sysdir-paired-dirhelper-sandbox-container-datavault-user-local-dir-source-libtrace-probe.json'
lsd=read(lsd_path)
selected=profile['source_runtime']
assert build['full_libsystem_kernel_source_build'] and build['complete_source_files']==874
assert not build['full_darling_rebuild'] and not build['installed']
for item in build['sources']:assert digest(item['source'])==item['sha256']
for path,sha in build['metadata_source_headers'].items():assert digest(path)==sha
assert digest('runtime/metadata-kernel-source/libsystem_kernel.dylib')==build['binary_sha256']
for result in [test,foundation,version,sdks,lsd]:
    assert result['source_runtime']==selected and result['source_kernel']==build
    if 'log' in result:assert digest(result['log'])==result['log_sha256']
    for path,sha in result.get('logs',{}).items():assert digest(path)==sha
assert test['runtime_execution_verified'] and test['exit_status']==0
assert test['source_sha256']==digest('fixtures/hello/metadata-kernel.c')
assert test['binary_sha256']==digest('artifacts/metadata-kernel')
match=re.search(r'METADATA_KERNEL_PASS checks=(\d+) unique_filesystems=(\d+)',(root/test['log']).read_text());assert match
assert foundation['exit_status']==0 and foundation['Foundation_metadata_fixture_passed']
assert foundation['fixture_source_sha256']==digest('fixtures/hello/coretypes-resource-values.m')
assert foundation['fixture_binary_sha256']==digest('artifacts/coretypes-resource-values')
assert 'CORETYPES_METADATA_RESULT directory=1 attributes=1 enumeration=3 errors=0' in foundation['diagnostic']
assert version['exit_status']==0 and 'Xcode 26.6\nBuild version 17F113' in version['diagnostic']
assert sdks['exit_status']==255 and 'Symbol not found: _OBJC_CLASS_$_CALayerContext' in sdks['diagnostic']
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
assert digest(original)==version['original_xcodebuild_sha256']==sdks['original_xcodebuild_sha256']==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
assert not lsd['UTI_functional_execution_verified'] and lsd['exit_status']!=0
assert lsd['original_binary_sha256']==lsd['staged_binary_sha256']==digest('runtime/native-lsd/lsd')
assert len(lsd['selected_job']['MachServices'])==13
assert lsd['paired_dirhelper_job']['MachServices']=={'com.apple.bsd.dirhelper':True}
assert 'Symbol not found: _container_query_create' in lsd['daemon_diagnostic']
assert 'Error -43 registering path /System/Library/CoreServices/CoreTypes.bundle' in lsd['daemon_diagnostic']
assert 'Error -50 registering path /System/Library/CoreServices/CoreTypes.bundle' not in lsd['daemon_diagnostic']
assert 'NATIVE_UTI_PREFERRED_EXTENSION_OK public.plain-text txt' in lsd['diagnostic']
xnu=root/'vendor/darling/src/external/xnu'
source_paths=[
 'darling/src/libsystem_kernel/emulation/include/xnu_syscall/bsd/helper/xattr/getattrlist_generic.c',
 'darling/src/libsystem_kernel/emulation/include/conversion/stat/common.h',
 'darling/src/libsystem_kernel/emulation/include/xnu_syscall/bsd/impl/xattr/getattrlistbulk.h',
 'darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/impl/xattr/getattrlistbulk.c',
 'darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/impl/stat/getfsstat.c',
 'darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/impl/stat/statfs.c',
 'darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/impl/stat/fstatfs.c']
patch=subprocess.check_output(['git','diff','--binary','--',*source_paths],cwd=xnu)
new='darling/src/libsystem_kernel/emulation/include/xnu_syscall/bsd/helper/xattr/metadata_linux.h'
assert subprocess.run(['git','ls-files','--error-unmatch',new],cwd=xnu,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
extra=subprocess.run(['git','diff','--no-index','--binary','--','/dev/null',new],cwd=xnu,capture_output=True);assert extra.returncode==1
patch+=extra.stdout
patch_name='artifacts/darling-metadata-kernel.patch';pending=root/(patch_name+'.pending');pending.write_bytes(patch);pending.replace(root/patch_name)
subprocess.run(['git','apply','--reverse','--check',str(root/patch_name)],cwd=xnu,check=True)
paths=['artifacts/metadata-kernel-source-build.json','artifacts/metadata-kernel-test.json','artifacts/metadata-kernel-foundation-probe.json','artifacts/metadata-kernel-version-probe.json','artifacts/metadata-kernel-showsdks-probe.json',lsd_path,patch_name]
scripts=['build-libsystem-kernel-source.py','metadata-kernel-profile.py','test-metadata-kernel.py','probe-metadata-kernel.py','build-coretypes-resource-fixture.py','debug-metadata-kernel-foundation.py','probe-native-lsd.py','record-metadata-kernel-progress.py']
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),previous_report='artifacts/sysdir-metadata-progress.json',
    evidence={s:digest(s) for s in paths},scripts={'scripts/'+s:digest('scripts/'+s) for s in scripts},
    source={str((xnu/p).relative_to(root)):digest(str((xnu/p).relative_to(root))) for p in source_paths+[new]},
    selected_runtime=selected,full_libsystem_kernel_source_build=True,source_files_compiled=874,
    metadata_checks=int(match[1]),unique_filesystems_observed=int(match[2]),
    original_Foundation_URL_attributes_and_recursive_enumeration_verified=True,
    original_xcode_version_verified=True,sdk_listing_verified=False,full_UTI_client_verified=False,
    full_xcode_build_ready=False,signing_ready=False,installed_as_default=False,
    implementation_form='Direct Darling libsystem_kernel source changes: shared statx-backed attrlist metadata and returned/invalid attribute packing; real FD/path extended attributes and directory counts; statfs/fsid identity normalization across all three APIs and deduplicated Linux bind mounts; a real getdents64/getattrlistat bulk fallback with bounded, aligned records and sequential cookie retries. Complete 874-file kernel component rebuilt into a coherent private variant. Other selected source components and compatibility/reexport libraries remain; this is not a unified full Darling build. Original xcodebuild is unchanged.',
    limits=[
      'Bulk fallback does not yet lock a shared open file description across getdents and seek rollback; concurrent readers/seeks require a server offset lock. Tests prove sequential cursor/retry behavior only.',
      'An attribute-read error with FSOPT_PACK_INVAL_ATTRS returns the real error and retains the pending cookie; its complete type-dependent error record layout is not implemented. XNU NOCROSSMOUNT metadata at nested mountpoints is not fully reproduced.',
      'Only volume capabilities and supported-attribute masks are implemented. UUID, snapshot, other volume properties, ACL/added-time/document-generation/data-protection metadata remain unsupported or unadvertised. Existing Darling opaque Linux-format st_dev values are retained; native Darwin major/minor and stable filesystem IDs across fresh overlay mounts are unverified.',
      'The metadata fixture reads three genuine CoreTypes entries; it does not prove catalog registration. Native lsd now reports OSStatus -43 (ENOENT, translocation path) for CoreTypes instead of the previous -50, and later aborts on missing container_query_create. Its UTI client reaches identifier/preferred extension but fails before full conformance/URL completion; managed probe is nonzero.',
      'Latest original Xcode -version succeeds, -showsdks still fails on CALayerContext. Full project build/archive/signing/export remain incomplete.'])
destination='artifacts/metadata-kernel-progress.json';(root/destination).write_text(json.dumps(record,indent=2)+'\n')
state=read('artifacts/current-work-state.json');state.update(updated_at=record['checked_at'],primary_report=destination,goal_status='active',complete=False,
    active_build=dict(task='source-metadata-kernel-and-native-Foundation',running=False,report=destination),latest_implementation_form=record['implementation_form'],
    latest_staged_coreml_and_metal_blocker='Source metadata kernel passes real Foundation URL/attributes/recursive CoreTypes enumeration and 11444 checks. Native lsd still fails CoreTypes registration with ENOENT/-43 and later missing container_query_create; full UTI/database unavailable. Genuine -version passes; -showsdks still lacks CALayerContext. Complete build/archive/signing/export remain incomplete.')
state['next_work']=list(dict.fromkeys([
 'Diagnose native lsd CoreTypes registration ENOENT/-43 in the real translocation/bundle path. The URL/NSFileManager metadata and recursive enumeration fixture now passes with the source kernel; do not infer catalog registration from resource presence or that narrower pass.',
 'Restore the real container_query_create and subsequent required ContainerManager ABI used while lsd registers remote placeholders. Reuse original provider/source when possible; preserve actual query/error/lifetime semantics and do not fabricate container records or successful service responses.',
 'Complete remaining metadata backend semantics when required: shared-open-description bulk offset locking, invalid-attribute error records, mount crossing behavior, stable filesystem identity and actual unsupported volume/protection fields.',
]+[s for s in state['next_work'] if not s.startswith(('Implement real metadata in the shared source kernel','Restore the real container_query_create'))]))
state['last_verification']=list(dict.fromkeys(state['last_verification']+[
 'Complete 874-file source kernel metadata variant passes 11444 real filesystem/API checks and original Foundation directory metadata plus three recursively enumerated CoreTypes entries. Original Xcode -version passes and -showsdks remains CALayerContext failure. Paired native lsd attempts real registration but CoreTypes is still ENOENT/-43 and remote placeholders still lack container_query_create; full UTI and complete Xcode goal remain unverified.']))
state['latest_validation_reports']=list(dict.fromkeys(state['latest_validation_reports']+paths+[destination]))
state.setdefault('source_components',{}).update(metadata_kernel='artifacts/metadata-kernel-source-build.json',metadata_progress=destination)
state['latest_selected_runtime']=selected
(root/'artifacts/current-work-state.json').write_text(json.dumps(state,indent=2)+'\n')
print('Recorded source metadata kernel progress; full Xcode goal remains active')
