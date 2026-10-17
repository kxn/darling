#!/usr/bin/env python3
"""Publish checked source/native MobileGestalt and real source dyld progress."""

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

read=lambda n:json.loads((root/n).read_text());digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
p=runpy.run_path(str(root/'scripts/runnable-archs-profile.py'))['profile']();selected=p['source_runtime']
assert p['source_libdyld']['full_libdyld_source_build'] and p['source_libdyld']['complete_source_files']==29
assert p['source_libdyld']['original_exports_preserved']==180 and p['source_libdyld']['source_exports']==182
assert p['source_kernel']['complete_source_files']==875 and p['source_libtrace']['complete_source_files']==9
for v in selected.values():assert digest(v['path'])==v['sha256']
source=read('artifacts/mobilegestalt-source-build.json');assert source['full_component_source_build'] and source['complete_source_files']==1 and source['original_exports_preserved']==33
for key in ['source','header','cmake','library','object','original']:assert digest(source[key])==source[key+'_sha256']
source_test=read('artifacts/mobilegestalt-source-test.json');assert source_test['runtime_execution_verified'] and len(source_test['results'])==2
for n,sha in source_test['sources'].items():assert digest(n)==sha
assert source_test['reference_analysis_sha256']==digest('artifacts/mobilegestalt-version-callback-analysis.json')
for r in source_test['results']:
 assert r['exit_status']==0 and digest(r['log'])==r['log_sha256'] and digest(r['binary'])==r['binary_sha256']
assert 'cases=264 checks=1868' in (root/source_test['results'][0]['log']).read_text()
assert 'SOURCE_MOBILEGESTALT_ACTUAL_GUEST_METADATA_AND_TYPED_OBJECT_OK 26.2' in (root/source_test['results'][1]['log']).read_text()
paths={'archs':'artifacts/runnable-archs-source-test.json','architecture':'artifacts/mobilegestalt-native-source-dyld-architecture-probe.json','device_failure':'artifacts/mobilegestalt-native-source-dyld-device-probe.json','regressions':'artifacts/runnable-archs-runtime-regressions.json','version':'artifacts/runnable-archs-xcode-version.json','showsdks':'artifacts/runnable-archs-xcode-showsdks.json','lsd':'artifacts/native-lsd-runnable-archs-probe.json'}
results={k:read(n) for k,n in paths.items()}
for name,r in results.items():
 assert r['source_runtime']==selected
 for key in ['mobilegestalt_native','runnable_archs','source_libdyld']:
  assert r[key]==p[key]
 if 'log' in r:assert digest(r['log'])==r['log_sha256']
 for n,sha in r.get('logs',{}).items():assert digest(n)==sha
 if name not in ['device_failure','showsdks','regressions']:assert r['exit_status']==0
assert results['archs']['runtime_execution_verified'] and results['archs']['differential_cases']==788
assert results['archs']['source_sha256']==digest('fixtures/hello/runnable-archs.c') and results['archs']['binary_sha256']==digest('artifacts/runnable-archs')
assert results['archs']['redirect_header_sha256']==digest('fixtures/hello/runnable-archs-redirect.h')
assert results['archs']['native_analysis_sha256']==digest('artifacts/runnable-archs-native-analysis.json')
for name in ['architecture','device_failure']:
 r=results[name];assert r['source_sha256']==digest('fixtures/hello/mobilegestalt-native.m') and r['binary_sha256']==digest('artifacts/mobilegestalt-native')
assert results['architecture']['runtime_execution_verified']
assert 'NATIVE_MOBILEGESTALT_ARCHITECTURES_MATCH_REAL_DYLD_OK' in (root/results['architecture']['log']).read_text()
assert not results['device_failure']['runtime_execution_verified'] and results['device_failure']['exit_status']==1
failure=(root/results['device_failure']['log']).read_text();assert 'NATIVE_MOBILEGESTALT_QUERY_BEGIN MobileGestalt_copy_userAssignedDeviceName_obj' in failure and 'NATIVE_MOBILEGESTALT_SELECTED_DEVICE_QUERIES_RETURNED' not in failure
assert 'MobileGestalt_copy_productType_obj class=<nil> present=0' in failure
reg=results['regressions'];assert reg['runtime_execution_verified'] and len(reg['checks'])==3
for r in reg['checks']:
 assert r['verified'] and r['exit_status']==0 and digest(r['log'])==r['log_sha256']
 binary=next(x for x in r['command'] if x.startswith('/Volumes/SystemRoot/workspace/artifacts/'));assert digest(binary.removeprefix('/Volumes/SystemRoot/workspace/'))==r['binary_sha256']
lsd=results['lsd'];assert lsd['UTI_functional_execution_verified'] and not lsd['frozen_trace_comparison']
assert 'NATIVE_UTI_TYPED_TAG_CONFORMANCE_AND_URL_EXTENSION_OK' in lsd['diagnostic']
assert 'Error -43 registering path /System/Library/CoreServices/CoreTypes.bundle' not in lsd['daemon_diagnostic'] and 'Symbol not found:' not in lsd['daemon_diagnostic']
for arg in p['command']:
 if arg.startswith(('DYLD_LIBRARY_PATH=','DYLD_FRAMEWORK_PATH=')):
  k,v=arg.split('=',1);assert lsd['selected_job']['EnvironmentVariables'][k]==v
assert 'Xcode 26.6\nBuild version 17F113' in (root/results['version']['log']).read_text()
blocker='_CGImageSourceCopyProperties';assert results['showsdks']['exit_status']==255 and 'Symbol not found: '+blocker in (root/results['showsdks']['log']).read_text()
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild';assert digest(original)==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
for mode in ['version','showsdks']:assert results[mode]['original_xcodebuild_sha256']==digest(original)
allocator=read('artifacts/mobilegestalt-allocators-test.json');assert allocator['runtime_execution_verified'] and allocator['exit_status']==0
assert allocator['source_sha256']==digest('fixtures/hello/mobilegestalt-allocators.cpp') and allocator['binary_sha256']==digest('artifacts/mobilegestalt-allocators') and allocator['log_sha256']==digest(allocator['log'])
assert allocator['mobilegestalt_native']==p['mobilegestalt_native']
assert 'allocations=448' in (root/allocator['log']).read_text()
reference=read('vendor/apple-dyld-runnable/reference.json');assert reference['sha256']==digest('vendor/apple-dyld-runnable/utils.cpp')
upstream=(root/'vendor/apple-dyld-runnable/utils.cpp').read_text();a=upstream.index('#if !TARGET_OS_SIMULATOR\nstatic bool hasFile');b=upstream.index('\n\n\n\n\n#endif // !TARGET_OS_EXCLAVEKIT',a)
assert upstream[a:b] in (root/'vendor/darling/src/external/dyld/src/runnable_archs.c').read_text()
patches=[]
for repo,tracked,added,out in [
 ('vendor/darling',['src/libMobileGestalt/src/MobileGestalt.m','src/libMobileGestalt/include/MobileGestalt/MobileGestalt.h','src/libMobileGestalt/CMakeLists.txt'],[],'artifacts/darling-mobilegestalt-source.patch'),
 ('vendor/darling/src/external/dyld',['CMakeLists.txt','gen/usr/local/include/mach-o/dyld_priv.h','src/dyldAPIsInLibSystem.cpp'],['src/runnable_archs.c','include/mach-o/utils.h'],'artifacts/darling-runnable-archs-source.patch')]:
 patch=subprocess.check_output(['git','diff','--binary','--',*tracked],cwd=root/repo)
 for n in added:
  extra=subprocess.run(['git','diff','--no-index','--binary','--','/dev/null',n],cwd=root/repo,capture_output=True);assert extra.returncode==1;patch+=extra.stdout
 assert patch;pending=root/(out+'.pending');pending.write_bytes(patch);pending.replace(root/out)
 subprocess.run(['git','apply','--reverse','--check',str(root/out)],cwd=root/repo,check=True);patches.append(out)
evidence=list(paths.values())+patches+['artifacts/mobilegestalt-source-build.json','artifacts/mobilegestalt-source-test.json','artifacts/mobilegestalt-version-callback-analysis.json','artifacts/mobilegestalt-native-stage.json','artifacts/mobilegestalt-allocators-test.json','artifacts/runnable-archs-source-build.json','artifacts/runnable-archs-source-stage.json','artifacts/runnable-archs-native-analysis.json','vendor/apple-dyld-runnable/reference.json','vendor/apple-dyld-runnable/utils.cpp']
script_names=['build-mobilegestalt-source.py','mobilegestalt-source-profile.py','analyze-mobilegestalt-version.py','test-mobilegestalt-source.py','stage-mobilegestalt-native.py','mobilegestalt-native-profile.py','probe-mobilegestalt-native.py','test-mobilegestalt-allocators.py','build-libdyld-source.py','analyze-runnable-archs.py','stage-runnable-archs.py','runnable-archs-profile.py','test-runnable-archs.py','verify-runnable-archs-runtime.py','probe-native-layer-xcode.py','probe-native-lsd.py','record-mobilegestalt-progress.py']
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),previous_report='artifacts/log-hooks-progress.json',previous_goal_turn_classification='no_progress',current_goal_turn_classification='progress',source_runtime=selected,source_libdyld=p['source_libdyld'],source_mobilegestalt=source,mobilegestalt_native=p['mobilegestalt_native'],runnable_archs=p['runnable_archs'],evidence={n:digest(n) for n in evidence},scripts={'scripts/'+n:digest('scripts/'+n) for n in script_names},original_xcodebuild_sha256=digest(original),differential_cases=dict(source_version=264,source_version_assertions=1868,source_architectures=788),version_succeeded=True,native_lsd_and_UTI_succeeded=True,sdk_listing_succeeded=False,next_original_xcode_loader_blocker=blocker,goal_status='active',complete=False,full_xcode_build_ready=False,signing_ready=False,
 implementation_form='Complete 29-file Darling source libdyld, exported through a named libSystem umbrella reexport. Full original Intel MobileGestalt with its two real classes and original IOMobileFramebuffer/liboah dependencies; no MG backend-call override. Existing two C++ typed allocator imports in the dependencies delegate to standard new/delete without type-tag isolation. Separately, the one-file source MobileGestalt version implementation is differential-tested but is not the selected native provider. Existing source kernel/XPC/launchd/objc/logging and prior private bridges remain. Original xcodebuild is unchanged.',
 remaining_limits=[
 'Actual SDK listing still exits 255 on missing ImageIO CGImageSourceCopyProperties. No project build/archive/sign/export has succeeded.',
 'Native MobileGestalt productType currently returns nil. The full device probe exits 1 in userAssignedDeviceName; no specific crash cause has been proved. Returned identifier values were not audited for real hardware identity.',
 'Cache-name enumeration reproduces original metadata behavior. It does not add ARM/Rosetta execution support or prove all CPU-grade choices. The actual guest has no Cryptex cache and therefore returns the original x86_64 fallback.',
 'The allocator adapters ignore type tags and provide no typed allocation isolation.',
 'Source MobileGestalt only implements the examined version query family; it does not replace the selected full native MG ABI.',
 'The full Darling tree has not been rebuilt as one distribution. This remains a mixed private source/native/compatibility environment; default launcher selection is unchanged.',
 'Previous metadata, directory policy, signing/trust, GPU/window and XPC protocol limits remain.'])
destination='artifacts/mobilegestalt-progress.json';pending=root/(destination+'.pending');pending.write_text(json.dumps(record,indent=2)+'\n');pending.replace(root/destination)
state=read('artifacts/current-work-state.json');state.update(updated_at=record['checked_at'],primary_report=destination,goal_status='active',complete=False,latest_selected_runtime=selected,latest_implementation_form=record['implementation_form'],latest_xcode_loader_blocker=blocker,latest_staged_coreml_and_metal_blocker=blocker,active_build=dict(task='source-dyld-runnable-architectures-and-original-MobileGestalt',running=False,report=destination))
state['next_work']=list(dict.fromkeys([
 'Implement or restore actual ImageIO source-level properties required by unchanged ContentDeliveryServices/AppStoreService, beginning with CGImageSourceCopyProperties. Preserve source-global and image-index property distinctions and actual decoding/ownership; do not return fabricated dictionaries merely to pass the loader.',
 'Investigate the real native MobileGestalt userAssignedDeviceName query failure through SystemConfiguration. ProductType is currently nil; do not invent host identity or claim full metadata support.',
 'Continue original xcodebuild -showsdks, then original Unity-exported/CocoaPods project build/archive/sign/export on Linux with preserved CI commands.',
]+[s for s in state['next_work'] if not s.startswith(('Implement the actual MobileGestalt human-readable','Continue unchanged genuine xcodebuild -showsdks after MobileGestalt'))]))
state['last_verification']=list(dict.fromkeys(state['last_verification']+['Full 29-file source libdyld preserves 180 packaged exports and passes 788 original-instruction cache-enumeration cases, real loader eight-thread lifecycle, 57-image snapshot and original native TLV regression. Native MG device context/version/CPU and architecture array match the actual dyld provider. Source MG version differential: 264 cases / 1868 assertions. Existing allocator 448 allocations and bad_alloc pass. Original lsd/UTI and unchanged xcodebuild -version pass under the final combination; -showsdks fails on ImageIO CGImageSourceCopyProperties. Native productType nil and device-name failure remain.']))
state['latest_validation_reports']=list(dict.fromkeys(state['latest_validation_reports']+evidence+[destination]));state['source_components'].update(mobilegestalt='artifacts/mobilegestalt-source-build.json',mobilegestalt_execution='artifacts/mobilegestalt-source-test.json',mobilegestalt_native='artifacts/mobilegestalt-native-stage.json',dyld_runnable_architectures='artifacts/runnable-archs-source-build.json',dyld_runnable_execution='artifacts/runnable-archs-source-test.json',mobilegestalt_progress=destination)
pending=root/'artifacts/current-work-state.json.pending';pending.write_text(json.dumps(state,indent=2)+'\n');pending.replace(root/'artifacts/current-work-state.json');print('Recorded source/native MobileGestalt, source libdyld and actual ImageIO loader blocker; goal remains active')
