#!/usr/bin/env python3
"""Tie service execution, original Xcode probes, source builds and defaults together."""

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
import hashlib,json,subprocess
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

# A historical recorder must not replace the newer directory-service checkpoint.
if json.loads((root / 'artifacts/current-work-state.json').read_text()).get('primary_report') in {'artifacts/libtrace-directory-progress.json', 'artifacts/directory-runtime-progress.json', 'artifacts/directory-services-progress.json', 'artifacts/sysdir-metadata-progress.json', 'artifacts/metadata-kernel-progress.json', 'artifacts/mount-container-progress.json'}:
    print('Preserving the later source logging and directory-service checkpoint')
    raise SystemExit(0)
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
read=lambda p:json.loads((root/p).read_text())
feature=read('artifacts/xpc-service-source.json')
probe_path='artifacts/xcode-full-native-foundation-source-sandbox-probe.json';probe=read(probe_path)
assert len(feature['selected_runtime'])==6
for variable,item in feature['selected_runtime'].items():
    assert digest(item['path'])==item['sha256']==probe['source_runtime'][variable]['sha256']
assert feature['api_owner_matches_actual_xpc_release_backend']
assert feature['real_launchd_job_start_repeat_and_eight_restarts_verified']
assert feature['cold_and_restarted_actual_task_suspend_count_and_task_resume_verified']
for path,value in feature['logs'].items():assert digest(path)==value
for path,value in feature['native_reports'].items():assert digest(path)==value
for path,value in feature['source_build_reports'].items():assert digest(path)==value
assert digest('fixtures/hello/xpc-service-source.c')==feature['fixture_sha256']
assert digest('scripts/test-xpc-service-source.sh')==feature['test_driver_sha256']
assert digest('artifacts/xpc-service-source')==feature['binary_sha256']
for path,value in read('artifacts/libxpc-source.json')['source_configuration']['base_libraries'].items():
    assert digest(path)==value
kernel=read('artifacts/libsystem-kernel-source.json')['source_configuration']
assert digest(kernel['baseline'])==kernel['baseline_sha256']
for relative in ['artifacts/quarantine-source.json','artifacts/sandbox-source.json']:
    config=read(relative)['source_configuration']
    assert digest(config['baseline'])==config['baseline_sha256']
launchd=read('artifacts/launchd-source.json')['source_configuration']
assert digest(launchd['original_launchd'])==launchd['original_launchd_sha256']
server=read('artifacts/darlingserver-memory-entry.json')
assert digest('runtime/rootfs/usr/bin/darlingserver')==server['default_server_sha256']
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
assert digest(original)==probe['apple_xcodebuild_sha256']==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
regressions=['artifacts/xpc-connection-source.json','artifacts/source-runtime-integration.json',
    'artifacts/launch-service-stats.json','artifacts/libsystem-kernel-source.json',
    'artifacts/responsibility-source.json','artifacts/sandbox-source.json']
for relative in regressions:
    report=read(relative)
    if 'source_libxpc_sha256' in report:assert report['source_libxpc_sha256']==feature['source_libxpc_sha256']
    if 'source_launchd_sha256' in report:assert report['source_launchd_sha256']==feature['source_launchd_sha256']
    if 'selected_runtime' in report:
        assert report['selected_runtime']['libxpc']['sha256']==feature['source_libxpc_sha256']
candidate_path='artifacts/logging-support-native-probe.json';candidate=read(candidate_path)
for variable,item in candidate['source_runtime'].items():
    assert item['sha256']==feature['selected_runtime'][variable]['sha256']
assert digest(candidate['staged_framework'])==candidate['staged_framework_sha256']
assert digest(candidate['log'])==candidate['log_sha256']
assert 'OSLogDeserializedEventStream' in probe['latest_diagnostic'] and probe['exit_status']==255
assert 'CADisplay' in candidate['diagnostic'] and candidate['exit_status']==255
for repo,patch in [('vendor/darling/src/external/libxpc','artifacts/darling-libxpc-shmem.patch'),
        ('vendor/darling','artifacts/darling-launchd-service-stats.patch')]:
    subprocess.run(['git','-C',str(root/repo),'apply','--reverse','--check',str(root/patch)],check=True)
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),goal_complete=False,
    xpc_service_report_sha256=digest('artifacts/xpc-service-source.json'),
    original_probe=dict(path=probe_path,sha256=digest(probe_path),exit_status=255),
    native_logging_candidate_probe=dict(path=candidate_path,sha256=digest(candidate_path),exit_status=255),
    selected_runtime=feature['selected_runtime'],original_xcodebuild_sha256=digest(original),
    source_patches_reverse_check_passed=True,packaged_runtime_defaults_unchanged=True,
    regression_reports={p:digest(p) for p in regressions},full_xcode_build_ready=False,signing_ready=False)
(root/'artifacts/xpc-service-progress.json').write_text(json.dumps(report,indent=2)+'\n')
state_path=root/'artifacts/current-work-state.json';state=json.loads(state_path.read_text())
if state.get('primary_report') == 'artifacts/objc-source-progress.json':
    print('Preserving the later source objc4 checkpoint')
    raise SystemExit(0)
if state.get('primary_report')=='artifacts/uti-native-progress.json':
    print('Preserving the later UTI/runtime-support checkpoint')
    raise SystemExit(0)
if state.get('primary_report')=='artifacts/security-yield-progress.json':
    print('Verified XPC service checkpoint; preserved the newer Security/yield work state.')
    raise SystemExit(0)
state.update(updated_at=datetime.now(timezone.utc).isoformat(),goal_status='active',complete=False,
    latest_staged_coreml_and_metal_blocker='Six-source runtime with original native Foundation passes xpc_service_kickstart_with_flags binding and now exits 255 on missing OSLogDeserializedEventStream in LoggingSupport. A separately reconstructed original LoggingSupport (78 ObjC classes) advances the original Xcode loading diagnostic to missing CADisplay in staged QuartzCore; no logging API execution or full build claim.',
    latest_implementation_form='Full source builds of server/libxpc/launchd/kernel/quarantine/sandbox selected coherently. libxpc service objects, typed native kickstart protocol and real managed-job launchd start/restart/suspension are implemented in source. Existing external helpers/rebinding remain; LoggingSupport is an isolated original-code reconstruction experiment. No full Darling rebuild; packaged defaults and original Xcode unchanged.')
state['next_work']=[
    'Continue original xcodebuild from CADisplay with isolated native LoggingSupport candidate. The ordinary 30-image native-Foundation stage still lacks OSLogDeserializedEventStream. Inspect actual QuartzCore display class/provider and callers before implementation; do not insert an empty class. LoggingSupport metadata/code reconstruction advances binding only; event decoding/filtering/callback/data-source execution is unverified.',
    'Complete XPC service management beyond managed-job kickstart: user/login/gui/rendezvous-token domains, actual attach/notification Mach protocol (703/704/706), configurable service-instance environment/path/FD/binpref/run lifecycle and set_use_sec_transition_shims. Existing system-domain positive spawn, eight real kill/wait4/restarts, cold/restart Mach suspension and task_resume passed. Existing PID-domain lookup has no positive execution test. SIGCONT does not resume existing task_suspend backend; native entitlement authorization and successful-exec/check-in acknowledgments are incomplete.'
]+[s for s in state['next_work'] if not s.startswith(('Implement xpc_service_kickstart_with_flags',
    'Continue original xcodebuild from CADisplay','Complete XPC service management beyond managed-job kickstart'))]
state['last_verification'] = list(dict.fromkeys(state['last_verification'] + [
    'Darling source service objects and native-shaped subsystem 2/routine 702 kickstart passed three-component and six-component actual managed-job tests: queue/UUID ownership, actual API owner, malformed requests, real kernel-audit rejection of forged request/reply identity and incompatible packaged launchd timeout.',
    'Actual launchctl-loaded non-RunAtLoad job starts; repeated kickstart preserves PID and does not suspend an active process. Eight actual SIGKILL/wait4/replacement forks passed. Cold/restarted suspended tasks have Mach suspend_count=1 and no user entry until actual task_resume. SIGCONT backend difference remains recorded.',
    'After source libxpc/launchd changes all descendants were rebuilt and connection compatibility, source runtime/Mach shared memory/stats, full kernel, responsibility and sandbox regressions passed. Full source libxpc retains all 630 original exports and 112 launch reexports; now 639 exports.',
    'Original xcodebuild -showsdks now exits 255 on OSLogDeserializedEventStream in six-source native-Foundation stage; separate original LoggingSupport reconstruction (78 classes, unverified API execution) advances binding failure to CADisplay. Project build/archive/signing remain incomplete.'
]))
state['source_components'].update(xpc_service='artifacts/xpc-service-source.json',
    xpc_service_native_abi='artifacts/xpc-service-native-analysis.json',
    xpc_service_native_callers='artifacts/xpc-service-native-callers.json',
    xpc_service_integration='artifacts/xpc-service-progress.json',
    logging_stream_native_abi='artifacts/logging-stream-native-analysis.json',
    logging_support_candidate='artifacts/logging-support-native-probe.json')
state['latest_validation_reports'] += [p for p in ['artifacts/xpc-service-source.json','artifacts/xpc-service-progress.json',
    'artifacts/xpc-service-native-analysis.json','artifacts/xpc-service-native-callers.json',
    'artifacts/logging-stream-native-analysis.json',candidate_path] if p not in state['latest_validation_reports']]
state_path.write_text(json.dumps(state,indent=2)+'\n')
print('Recorded source service progress; original Xcode remains incomplete. Packaged defaults and source patches verified.')
