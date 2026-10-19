#!/usr/bin/env python3
"""Record actual shared FSEvents and original Xcode compilation evidence."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, runpy, subprocess

root = Path(__file__).resolve().parent.parent
read = lambda name: json.loads((root / name).read_text())
digest = lambda name: hashlib.sha256((root / name).read_bytes()).hexdigest()
resolve = runpy.run_path(str(root / 'scripts/resolve-evidence-history.py'))['resolve']
evidence = {}
def add(name, sha=None):
    name = resolve(str(name), sha) if sha else str(name)
    evidence[name] = digest(name)
    if sha: assert evidence[name] == sha, name
def walk(value):
    if isinstance(value, list):
        for item in value: walk(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, str) and isinstance(value.get(key + '_sha256'), str) and (root / item).is_file():
                add(item, value[key + '_sha256'])
            if key == 'sha256':
                for path_key in ['source', 'path', 'file']:
                    if path_key + '_sha256' not in value and isinstance(value.get(path_key), str) and (root / value[path_key]).is_file(): add(value[path_key], item)
            if isinstance(item, str) and re.fullmatch('[a-f0-9]{64}', item) and (root / key).is_file(): add(key, item)
            if isinstance(item, (dict, list)): walk(item)
def report(name):
    value = read(name); add(name); walk(value); return value

profile = runpy.run_path(str(root / 'scripts/xcode-tool-dispatch-runtime-profile.py'))['profile']()
for name in ['artifacts/global-fsevents-server-build.json', 'artifacts/global-fsevents-source-build.json',
             'artifacts/global-fsevents-stage.json', 'artifacts/vchroot-links-kernel-build.json', 'artifacts/vchroot-links-stage.json', 'artifacts/metadata-root-name-kernel-build.json', 'artifacts/metadata-root-name-stage.json', 'artifacts/xcode-tool-dispatch-stage.json','artifacts/xcode-tool-dispatch-stage-v2.json']:
    report(name)
linux = report('artifacts/fsevents-journal-linux-test.json'); assert linux['verified'] and linux['ASan_UBSan']
native = report('artifacts/global-fsevents-native-test-vchroot-links.json'); assert native['verified']
cache = report('artifacts/original-stat-cache-global-fsevents-test-vchroot-links.json'); assert cache['verified']
assert 'ORIGINAL_CACHE_IN_PLACE_HEADER_WRITE_INVALIDATES_OK' in (root / cache['log']).read_text()
real_sdk = report('artifacts/original-real-sdk-stat-cache-test.json'); assert real_sdk['verified']
product=report('artifacts/ios-cocoapods-product.json'); assert product['verified']
signing=report('artifacts/original-ios-adhoc-signing-probe.json'); assert not signing['adhoc_signing_verified']
assert 'AppleMobileFileIntegrity.framework' in (root/signing['log']).read_text()
report('artifacts/ruby-absolute-glob-analysis.json')
links_before = report('artifacts/vchroot-links-baseline.json'); assert links_before['verified']
links = report('artifacts/vchroot-links-fixed.json'); assert links['verified'] and links['checks'] == [176]
metadata=report('artifacts/metadata-root-name-fixed.json'); assert metadata['verified'] and metadata['checks']==[54]
report('artifacts/metadata-root-name-baseline.json')
program = report('artifacts/xcodebuild-produced-program.json'); assert program['verified']
mac_name = 'artifacts/xcode-service-runtime-vchroot-links-diagnostic-build-d12cd827b219.json'
mac = report(mac_name); mac_log = (root / mac['log']).read_text()
assert mac['exit_status'] == 0 and mac['UTI_preflight_verified']
assert all(marker in mac_log for marker in ['CompileC ', '\nLd ', '** BUILD SUCCEEDED **', 'SERVICE_RUNTIME_XCODE_STATUS 0'])
assert mac['source_runtime']['LINUXCODE_LIBSYSTEM_KERNEL']['sha256'] == links['source_runtime']['LINUXCODE_LIBSYSTEM_KERNEL']['sha256']
mac_outputs = {}
for directory in ['runtime/xcode-service-runtime/DerivedData/Build/Products', 'runtime/xcode-service-runtime/DerivedData/Build/Intermediates.noindex/XcodeSmoke.build']:
    for path in (root / directory).rglob('*'):
        if path.is_file():
            name = str(path.relative_to(root)); add(name); mac_outputs[name] = digest(name)
ios = None
for path in sorted((root / 'artifacts').glob('xcode-service-runtime-tool-dispatch-diagnostic-build-*.json'),key=lambda path:path.stat().st_mtime):
    candidate = read(str(path.relative_to(root)))
    if candidate.get('xcode_arguments_file') == 'config/ios-cocoapods-build-arguments.json':
        ios = report(str(path.relative_to(root)))
        ios['report_path'] = str(path.relative_to(root))
if (root / 'artifacts/ios-cocoapods-install.json').exists():
    installation = report('artifacts/ios-cocoapods-install.json')
else: installation = None
ios_log = (root / ios['log']).read_text() if ios else ''
ios_succeeded = bool(ios and ios['exit_status'] == 0 and '** BUILD SUCCEEDED **' in ios_log and 'SERVICE_RUNTIME_XCODE_STATUS 0' in ios_log)
if ios_succeeded:
    assert '\nSCOPED_RUBY_OPENSSL_OK\n' in ios_log
    assert '\nSCOPED_XCRUN_ORIGINAL_CLANG_FOUND /Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang\n' in ios_log
    assert ios['prebuild_command_verified']
for name in ['scripts/build-global-fsevents-server.py', 'scripts/stage-global-fsevents-runtime.py',
             'scripts/global-fsevents-runtime-profile.py', 'scripts/test-fsevents-journal-linux.py',
             'scripts/test-global-fsevents-native.py', 'scripts/test-original-stat-cache.py',
             'scripts/test-original-real-sdk-stat-cache.py', 'scripts/stage-vchroot-links-runtime.py',
             'scripts/verify-ios-cocoapods-product.py','scripts/probe-original-ios-signing.py',
             'scripts/vchroot-links-runtime-profile.py', 'scripts/test-vchroot-links.py',
             'scripts/install-ios-cocoapods-fixture.py', 'scripts/probe-xcode-service-runtime.py',
             'scripts/stage-metadata-root-name-runtime.py','scripts/metadata-root-name-runtime-profile.py','scripts/test-metadata-root-name.py',
             'scripts/stage-xcode-tool-dispatch-runtime.py','scripts/xcode-tool-dispatch-runtime-profile.py',
             'fixtures/hello/metadata-root-name.c','config/ios-cocoapods-prebuild-arguments.json',
             'artifacts/ios-cocoapods-first-build-failure/manifest.json',
             'runtime/recovery/macOS Base System/usr/bin/codesign','runtime/state/prefix/usr/bin/codesign',
             'scripts/fatal-signal-runtime-profile.py', 'scripts/fsevents-history-profile.py',
             'scripts/resolve-evidence-history.py', 'scripts/record-global-fsevents-progress.py',
             'artifacts/global-fsevents-initial-history/manifest.json', 'artifacts/global-fsevents-stack-failure-history/manifest.json',
             'logs/global-fsevents-server-stack-fault-kernel.log', 'logs/original-real-sdk-core.gdb.log',
             'logs/ruby-openssl-xcode-overrides.log', 'logs/ruby-openssl-scoped-ruby.log', 'config/ios-cocoapods-build-arguments.json']:
    add(name)
for repository, files, patch in [
    ('vendor/darlingserver', ['CMakeLists.txt', 'src/call.cpp', 'src/fsevents-device.cpp', 'internal-include/darlingserver/fsevents-device.hpp'], 'artifacts/darlingserver-global-fsevents-source.patch'),
    ('vendor/darling', ['src/frameworks/CoreServices/src/FSEvents', 'src/frameworks/CoreServices/include/FSEvents/FSEvents.h'], 'artifacts/darling-global-fsevents-source.patch'),
    ('vendor/darling/src/external/xnu', ['darling/src/libsystem_kernel/emulation/src/linux_premigration/vchroot_userspace.c', 'darling/src/libsystem_kernel/emulation/include/linux_premigration/vchroot_expand.h', 'darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/impl/stat/fstatat.c', 'darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/impl/stat/lstat.c', 'darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/impl/fcntl/openat.c','darling/src/libsystem_kernel/emulation/include/xnu_syscall/bsd/helper/xattr/getattrlist_generic.c'], 'artifacts/xnu-vchroot-links-source.patch')]:
    data = subprocess.check_output(['git', '-C', str(root / repository), 'diff', 'HEAD', '--', *files])
    if repository=='vendor/darlingserver':
        for new_file in ['src/fsevents-journal.cpp','internal-include/darlingserver/fsevents-journal.hpp']:
            diff=subprocess.run(['git','diff','--no-index','--','/dev/null',new_file],cwd=root/repository,stdout=subprocess.PIPE,check=False)
            assert diff.returncode==1
            data+=diff.stdout
    (root / patch).write_bytes(data); add(patch)
    subprocess.run(['git', '-C', str(root / repository), 'apply', '--reverse', '--check', str(root / patch)], check=True)
# Include direct hashes of the new journal source as well as its complete patch.
for name in ['vendor/darlingserver/src/fsevents-journal.cpp', 'vendor/darlingserver/internal-include/darlingserver/fsevents-journal.hpp']:
    add(name)
for manifest in (root/'artifacts/xcode-service-probe-history').glob('*/manifest.json'):
    entries=read(str(manifest.relative_to(root)))
    if any('tool-dispatch-diagnostic-build-c53d8a856d7e' in name for name in entries):
        add(str(manifest.relative_to(root)))
        for item in entries.values():add(item['archived'],item['sha256'])
for path in (root / 'fixtures/iOSCocoaPodsSmoke').rglob('*'):
    if path.is_file() and not path.name.startswith('core.') and '.git' not in path.parts: add(str(path.relative_to(root)))
ios_native_status=re.findall(r'SERVICE_RUNTIME_XCODE_STATUS (\d+)',ios_log)
record = dict(checked_at=datetime.now(timezone.utc).isoformat(), goal_status='active', complete=False,
    source_runtime=profile['source_runtime'], source_fsevents=profile['source_global_fsevents_framework'],
    shared_global_event_ids_implemented=True, durable_ID_high_water=True, durable_event_history=False,
    replay_history_capacity=8192, history_loss_requires_rescan=True, counter_queries_do_not_allocate_event_IDs=True,
    linux_ASan_UBSan_checks=linux['checks'], native_history_checks=native['cases'][0]['checks'], native_flush_checks=native['cases'][1]['checks'],
    original_stat_cache_initial_reuse_mutation_and_Clang_consumer_verified=True,
    original_full_SDK_stat_cache_generation_reuse_and_Clang_consumer_verified=True,
    server_RPC_fiber_automatic_buffer_overflow_fixed=True, vchroot_cumulative_symlink_limit=32,
    native_vchroot_checks=176, native_vchroot_64KiB_thread_verified=True,
    original_macos_test_project_build_succeeded=True, original_macos_test_project=mac_name,
    original_macos_test_project_sha256=digest(mac_name), macos_outputs=mac_outputs,
    produced_macos_program_execution_verified=True, actual_project_compilation_started=True,
    native_virtual_root_metadata_checks=54,
    ios_CocoaPods_installation_verified=bool(ios and ios.get('prebuild_command_verified')), ios_CocoaPods_project_build_succeeded=ios_succeeded,
    ios_CocoaPods_project=ios.get('report_path') if ios else None,
    ios_CocoaPods_project_sha256=digest(ios['report_path']) if ios else None,
    ios_CocoaPods_native_exit_status=int(ios_native_status[-1]) if ios_native_status else None,
    ios_CocoaPods_wrapper_exit_status=ios['exit_status'] if ios else None,
    engine_generated_project_verified=False, Unity_project_build_verified=False, UE_project_build_verified=False,
    signing_ready=False, full_xcode_build_ready=False, default_entry_promoted=False,
    original_project_uses_explicit_permissive_coreservices_policy=True, strict_Sandbox_enforcement_verified=False,
    remaining_FSEvents_limits=['Replay is volatile; restart reports real coverage loss.', 'Origin PID/IgnoreSelf/MarkSelf unsupported.', 'External-root ancestor changes, mount replacement and nested bind aliases are not fully verified.'],
    current_observed_failure='Original macOS project and iOS CocoaPods App build successfully without signing. Original codesign fails loading AppleMobileFileIntegrity.framework; no native status marker returned. Unity/UE and provisioned signing remain incomplete.',
    next_work=['Restore the actual AppleMobileFileIntegrity dependency of original codesign and verify real signatures, then complete archive/export and actual Unity/UE exported projects with CocoaPods.',
               'Integrate verified runtime and per-tool library scope behind existing CI commands; default entry is not promoted.',
               'Resolve remaining strict CoreServices policy, runtime lifecycle, resource-tool and filesystem event limitations based on actual failures.'],
    evidence=evidence)
(root / 'artifacts/global-fsevents-progress.json').write_text(json.dumps(record, indent=2) + '\n')
print('Recorded', len(evidence), 'hashes; original macOS project builds and runs; iOS/CocoaPods/signing/engine goal remains active.')
