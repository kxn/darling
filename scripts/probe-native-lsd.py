#!/usr/bin/env python3
"""Start the original Intel lsd as a managed job in one private Darling session."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, fcntl, hashlib, json, os, plistlib, shutil, subprocess

root = Path(__file__).resolve().parent.parent
digest = lambda p: hashlib.sha256((root / p).read_bytes()).hexdigest()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-libtrace', action='store_true')
parser.add_argument('--user-local-dir-export', action='store_true')
parser.add_argument('--rootless-datavault-export', action='store_true')
parser.add_argument('--sandbox-container', action='store_true')
parser.add_argument('--with-dirhelper', action='store_true')
parser.add_argument('--native-sysdir', action='store_true')
parser.add_argument('--metadata-kernel', action='store_true')
parser.add_argument('--native-container-manager', action='store_true')
parser.add_argument('--xtrace', action='store_true')
parser.add_argument('--debug-gate', action='store_true')
parser.add_argument('--mount-path-kernel', action='store_true')
parser.add_argument('--layer-log',action='store_true',help='Use the current source bitmap context and log enablement profile')
parser.add_argument('--native-message',action='store_true',help='Also select the original log-message formatter forwarder')
parser.add_argument('--latest-profile',choices=['log-hooks','container-persona','runnable-archs','imageio-native','combine-native','fsevents-source','fsevents-flush','foundation-coherent'],help='Select a verified current profile and a compact distinct report name')
parser.add_argument('--frozen-trace-comparison',action='store_true',help='Diagnostic only: compare the preserved pre-hook libtrace binary, not a current source build')
args = parser.parse_args()
if args.user_local_dir_export and not args.source_libtrace: parser.error('user directory export requires source libtrace')
if args.rootless_datavault_export and not args.user_local_dir_export: parser.error('data vault export requires user directory export')
if args.sandbox_container and not args.rootless_datavault_export: parser.error('sandbox container requires data vault export')
if args.with_dirhelper and not args.sandbox_container: parser.error('paired dirhelper requires sandbox container profile')
if args.native_sysdir and not args.sandbox_container: parser.error('native sysdir requires sandbox container')
if args.metadata_kernel and not (args.native_sysdir and args.with_dirhelper): parser.error('metadata kernel requires paired native-sysdir profile')
if (args.native_container_manager or args.xtrace) and not args.metadata_kernel: parser.error('container manager and xtrace require the metadata kernel profile')
if args.mount_path_kernel and not args.metadata_kernel: parser.error('mount path kernel requires metadata kernel profile')
if args.debug_gate and args.xtrace: parser.error('Choose a single diagnostic mechanism')
if args.layer_log and not(args.mount_path_kernel and args.native_container_manager):parser.error('layer/log profile requires mount-path kernel and native ContainerManager')
if args.native_message and not args.layer_log:parser.error('native message formatter requires layer/log profile')
if args.latest_profile and not args.native_message:parser.error('latest profile requires the complete native-message profile flags')
if args.frozen_trace_comparison and not args.latest_profile:parser.error('frozen comparison requires an explicit latest profile')
suffix = ('-mount-path' if args.mount_path_kernel else '') + ('-debug-gate' if args.debug_gate else '') + ('-xtrace' if args.xtrace else '') + ('-container-manager' if args.native_container_manager else '') + ('-metadata-kernel' if args.metadata_kernel else '') + ('-sysdir' if args.native_sysdir else '') + ('-paired-dirhelper' if args.with_dirhelper else '') + ('-sandbox-container' if args.sandbox_container else '') + ('-datavault' if args.rootless_datavault_export else '') + ('-user-local-dir' if args.user_local_dir_export else '') + ('-source-libtrace' if args.source_libtrace else '')
profile_name = 'artifacts/uniform-type-identifiers-native-xcode-' + ('sysdir-' if args.native_sysdir else '') + ('sandbox-container-nounlink-typed-malloc-simple-log-' if args.sandbox_container else '') + ('datavault-' if args.rootless_datavault_export else '') + ('user-local-dir-' if args.user_local_dir_export else '') + ('source-libtrace-' if args.source_libtrace else '') + 'source-objc-support-showsdks.json'
profile = json.loads((root / profile_name).read_text())
if args.layer_log:suffix='-layer-log'+suffix
if args.native_message:suffix='-native-message'+suffix
if args.latest_profile:suffix='-'+args.latest_profile+('-debug-gate' if args.debug_gate else '')
if args.frozen_trace_comparison:suffix+='-trace8-comparison'
if args.metadata_kernel:
    import runpy
    selected = runpy.run_path(str(root/('scripts/mount-path-kernel-profile.py' if args.mount_path_kernel else 'scripts/metadata-kernel-profile.py')))['profile']()
    assert selected['base_profile'] == profile_name
    profile.update(command=selected['command'], source_runtime=selected['source_runtime'], source_kernel=selected['source_kernel'])
if args.native_container_manager:
    selected=runpy.run_path(str(root/'scripts/container-manager-profile.py'))['profile'](kernel_profile=selected)
    profile.update(command=selected['command'], container_manager=selected['container_manager'])
if args.layer_log:
    selected_name=args.latest_profile or ('native-log-message' if args.native_message else 'log-enablement')
    selected=runpy.run_path(str(root/('scripts/'+selected_name+'-profile.py')))['profile']()
    profile.update(selected)
    profile['source_libtrace']=selected.get('source_libtrace',selected['log_enablement']['source_build'])
if args.frozen_trace_comparison:
    frozen=json.loads((root/'artifacts/libtrace-enablement-source-build.json').read_text())
    assert digest(frozen['library'])==frozen['library_sha256']
    command=list(profile['command']);i=next(i for i,v in enumerate(command) if v.startswith('DYLD_LIBRARY_PATH='))
    command[i]='DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/'+str(Path(frozen['library']).parent)+':'+command[i].split('=',1)[1]
    profile.update(command=command,source_libtrace=frozen)
objc = profile.get('source_objc') or json.loads((root / 'artifacts/objc-source-build.json').read_text())
assert digest(objc['library']) == objc['library_sha256'] == profile['source_objc']['library_sha256']
recovery = root / 'runtime/recovery/macOS Base System'
base = root / 'runtime/native-lsd'
base.mkdir(exist_ok=True)
guest = '/Volumes/SystemRoot/workspace/'
binary = base / 'lsd'
source = recovery / 'usr/libexec/lsd'
original_plist = recovery / 'System/Library/LaunchDaemons/com.apple.lsd.plist'
job = plistlib.loads(original_plist.read_bytes())
assert job['Label'] == 'com.apple.lsd' and job['ProgramArguments'] == ['/usr/libexec/lsd', 'runAsRoot']
assert job['MachServices']['com.apple.lsd.mapdb']
environment = os.environ.copy()
for name, item in profile['source_runtime'].items():
    assert digest(item['path']) == item['sha256']
    environment[name] = str(root / item['path'])
settings = {}
for argument in profile['command']:
    if argument.startswith(('DYLD_LIBRARY_PATH=', 'DYLD_FRAMEWORK_PATH=', 'OBJC_DISABLE_TAGGED_POINTERS=')):
        key, value = argument.split('=', 1)
        settings[key] = value
job['ProgramArguments'][0] = guest + 'runtime/native-lsd/lsd'
job['EnvironmentVariables'] = {**job['EnvironmentVariables'], **settings}
if args.source_libtrace: job['EnvironmentVariables']['DARLING_OS_LOG_STDERR'] = '1'
daemon_log = 'logs/native-lsd' + suffix + '-daemon.log'
job['StandardOutPath'] = guest + daemon_log
job['StandardErrorPath'] = guest + daemon_log
job['RunAtLoad'] = True
if args.debug_gate:
    assert (root/'runtime/launch-debug-gate/libDarlingLaunchDebugGate.dylib').is_file()
    job['EnvironmentVariables']['DYLD_INSERT_LIBRARIES']=guest+'runtime/launch-debug-gate/libDarlingLaunchDebugGate.dylib'
trace_log=None
if args.xtrace:
    trace_log='logs/native-lsd'+suffix+'-syscalls.log'
    job['EnvironmentVariables'].update(DYLD_INSERT_LIBRARIES='/usr/lib/darling/libxtrace.dylib',XTRACE_NO_COLOR='1',XTRACE_LOG_FILE=guest+trace_log)
    with (root/'runtime/session.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);(root/trace_log).write_text('')
plist = base / ('com.apple.lsd' + suffix + '.plist')
script = base / ('session' + suffix + '.sh')
with (root / 'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    pending = binary.with_suffix('.pending')
    shutil.copyfile(source, pending)
    pending.chmod(0o755)
    pending.replace(binary)
    plist.write_bytes(plistlib.dumps(job))
    plist.chmod(0o644)
    (root / daemon_log).write_text('')
script.write_text('''#!/bin/bash
set +e
launchctl load /Volumes/SystemRoot/workspace/runtime/native-lsd/com.apple.lsd.plist
loaded=$?
echo NATIVE_LSD_LAUNCHCTL_LOAD_STATUS "$loaded"
if [ "$loaded" -ne 0 ]; then exit "$loaded"; fi
trap 'launchctl remove com.apple.lsd >/dev/null 2>&1' EXIT
sleep 2
state=$(launchctl list com.apple.lsd)
printf '%s\n' "$state"
case "$state" in
*'"PID"'*) ;;
*)
    echo NATIVE_LSD_NO_RUNNING_PID_AFTER_START
    exit 1
    ;;
esac
echo NATIVE_LSD_CLIENT_BEGIN
/Volumes/SystemRoot/workspace/artifacts/uniform-type-identifiers-native
status=$?
echo NATIVE_LSD_CLIENT_STATUS "$status"
launchctl list com.apple.lsd
exit "$status"
'''.replace('/runtime/native-lsd/com.apple.lsd.plist', '/runtime/native-lsd/' + plist.name))
helper_log = None
helper_job = None
if args.with_dirhelper:
    previous = json.loads((root / ('artifacts/native-dirhelper-' + ('sysdir-' if args.native_sysdir else '') + 'sandbox-container-nounlink-typed-malloc-source-simple-log-probe.json')).read_text())
    assert previous['runtime_execution_verified']
    assert digest('runtime/native-dirhelper/dirhelper') == previous['original_binary_sha256']
    helper_job = dict(previous['job'])
    helper_job['EnvironmentVariables'] = dict(previous['job']['EnvironmentVariables'])
    for key, value in settings.items():
        if args.native_container_manager: helper_job['EnvironmentVariables'][key]=value
        else: assert helper_job['EnvironmentVariables'][key] == value
    helper_log = 'logs/native-lsd' + suffix + '-dirhelper.log'
    helper_job['StandardOutPath'] = helper_job['StandardErrorPath'] = guest + helper_log
    helper_plist = base / ('com.apple.bsd.dirhelper' + suffix + '.plist')
    with (root / 'runtime/session.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        helper_plist.write_bytes(plistlib.dumps(helper_job)); helper_plist.chmod(0o644)
        (root / helper_log).write_text('')
    body = script.read_text()
    body = body.replace('set +e\n', 'set +e\nlaunchctl load ' + guest + str(helper_plist.relative_to(root)) + '\nloaded=$?\necho NATIVE_LSD_DIRHELPER_LOAD_STATUS "$loaded"\nif [ "$loaded" -ne 0 ]; then exit "$loaded"; fi\n')
    body = body.replace("trap 'launchctl remove com.apple.lsd >/dev/null 2>&1' EXIT", "trap 'launchctl remove com.apple.lsd >/dev/null 2>&1; launchctl remove com.apple.bsd.dirhelper >/dev/null 2>&1' EXIT")
    body = body.replace('echo NATIVE_LSD_CLIENT_BEGIN', 'launchctl list com.apple.bsd.dirhelper\necho NATIVE_LSD_CLIENT_BEGIN')
    script.write_text(body)
command = profile['command'][:-2] + ['/bin/bash', guest + str(script.relative_to(root))]
if args.debug_gate: command[3]='180'
log = 'logs/native-lsd' + suffix + '-session.log'
with (root / log).open('w') as stream:
    result = subprocess.run(command, cwd=root, env=environment, stdout=stream, stderr=subprocess.STDOUT)
text = (root / log).read_text()
daemon = (root / daemon_log).read_text()
report = dict(checked_at=datetime.now(timezone.utc).isoformat(), installed=False,
    frozen_trace_comparison=args.frozen_trace_comparison,
    mount_path_kernel=args.mount_path_kernel, metadata_kernel=args.metadata_kernel, source_kernel=profile.get('source_kernel'), container_manager=profile.get('container_manager'), xtrace=args.xtrace, debug_gate=args.debug_gate,
    command=command, source_runtime=profile['source_runtime'], source_objc=objc,
    source_libtrace=profile.get('source_libtrace'),
    native_layer_support=profile.get('native_layer_support'), native_layer_context=profile.get('native_layer_context'), log_enablement=profile.get('log_enablement'),
    native_log_message=profile.get('native_log_message'),
    log_hooks=profile.get('log_hooks'), container_persona=profile.get('container_persona'),
    mobilegestalt_native=profile.get('mobilegestalt_native'), runnable_archs=profile.get('runnable_archs'), source_libdyld=profile.get('source_libdyld'),
    source_selector=profile.get('source_selector'), foundation_coherent=profile.get('foundation_coherent'), source_fsevents=profile.get('source_fsevents'), combine_native=profile.get('combine_native'), imageio_native=profile.get('imageio_native'), imageio_cg_constants=profile.get('imageio_cg_constants'), simd_matrix=profile.get('simd_matrix'), imageio_legacy_key=profile.get('imageio_legacy_key'),
    user_local_dir_export=profile.get('user_local_dir_export'),
    rootless_datavault_export=profile.get('rootless_datavault_export'),
    source_simple_log=profile.get('source_simple_log'), typed_malloc=profile.get('typed_malloc'),
    nounlink_export=profile.get('nounlink_export'), sandbox_container=profile.get('sandbox_container'), native_sysdir=profile.get('native_sysdir'),
    paired_dirhelper_job=helper_job,
    original_binary_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), staged_binary_sha256=digest('runtime/native-lsd/lsd'),
    original_job_sha256=hashlib.sha256(original_plist.read_bytes()).hexdigest(), selected_job=job,
    exit_status=result.returncode, logs={p: digest(p) for p in [log, daemon_log] + ([helper_log] if helper_log else []) + ([trace_log] if trace_log else [])},
    diagnostic=text, daemon_diagnostic=daemon,
    UTI_functional_execution_verified=result.returncode == 0 and 'NATIVE_UTI_TYPED_TAG_CONFORMANCE_AND_URL_EXTENSION_OK\n' in text,
    full_xcode_build_ready=False, signing_ready=False)
assert report['original_binary_sha256'] == report['staged_binary_sha256']
(root / ('artifacts/native-lsd' + suffix + '-probe.json')).write_text(json.dumps(report, indent=2) + '\n')
print(text[-3500:])
print('DAEMON:', daemon[-3500:])
print('Managed original lsd probe:', result.returncode)
raise SystemExit(0 if report['UTI_functional_execution_verified'] else 1)
