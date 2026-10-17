#!/usr/bin/env python3
"""Called by setup-xcode only after all base/toolchain/CocoaPods checks pass."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import plistlib

project = Path(__file__).resolve().parent.parent
path = project / 'artifacts/environment.json'
data = json.loads(path.read_text()) if path.exists() else {}
data.pop('full_build_blocker', None)
xcode = project / 'runtime/state/prefix/Applications/Xcode.app'
version = plistlib.loads((xcode/'Contents/version.plist').read_bytes())
probes = json.loads((project/'artifacts/xcode-probes.json').read_text())

def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            value.update(chunk)
    return value.hexdigest()

binaries = {}
for name, relative in {
    'xcodebuild': 'Contents/Developer/usr/bin/xcodebuild',
    'clang': 'Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang',
    'ld': 'Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/ld',
}.items():
    actual = digest(xcode/relative)
    original = digest(project/'runtime/xcode-extract/Xcode.app'/relative)
    if actual != original:
        raise ValueError('Apple binary differs from XIP extraction: '+name)
    binaries[name] = actual

data.update({
    'last_base_validation': datetime.now(timezone.utc).isoformat(),
    'host_architecture': 'x86_64',
    'ubuntu_base': '24.04.5 amd64',
    'darling_release': 'v0.1.20260608',
    'darling_package': '0.1.20260609~noble',
    'darling_runtime_revision': 'e947f0d5',
    'kernel_module_required': False,
    'runtime_requires_sudo': False,
    'xcode_installed': True,
    'xcode_version': version['CFBundleShortVersionString'],
    'xcode_build': version['ProductBuildVersion'],
    'apple_binary_sha256': binaries,
    'apple_binaries_match_xip': True,
    'smoke_tests': 'passed',
    'host_smoke_diff_bytes': (project/'logs/host-smoke.diff').stat().st_size,
    'toolchain_checks': ['xcodebuild-version', 'parallel-unfair-locks', 'ios-c-compile-link',
        'ios-cpp-compile-link-dsym', 'macos-compile-link-run', 'cpp-bad-function-call'],
    'cocoapods_version': '1.16.2',
    'rubygems_version': '3.4.22',
    'ruby_version': '2.6.3',
    'darwin_ffi_version': '1.17.2',
    'local_pod_integration': 'passed',
    'swift_runtime_version': '6.3.3',
    'swift_runtime_package_sha256': 'ee82e57774d6650f94aa06302435d6f44a055b9411698db8ecb85d9a3bcc91d0',
    'swift_runtime_checks': ['collections', 'Foundation-JSON', 'async-task-group', 'original-Apple-demangler'],
    'swift_system_revision': '0b30161977799fd949f7f6848586b82ff6764f73',
    'compatibility_reports': ['artifacts/cryptokit-compat.json', 'artifacts/combine-compat.json',
        'artifacts/swift-system-compat.json', 'artifacts/applearchive-compat.json',
        'artifacts/uniform-types-compat.json', 'artifacts/osanalytics-compat.json',
        'artifacts/softlinking-compat.json', 'artifacts/coreentitlements-compat.json',
        'artifacts/spindump-compat.json', 'artifacts/amsupport-compat.json',
        'artifacts/fdr-compat.json', 'artifacts/remote-service-discovery-compat.json',
        'artifacts/core-emoji-compat.json', 'artifacts/feature-flags-compat.json',
        'artifacts/constant-numbers-compat.json', 'artifacts/cache-tls-compat.json',
        'artifacts/swift-os-compat.json', 'artifacts/native-metrics-compat.json',
        'artifacts/symptoms-compat.json', 'artifacts/host-cpu-compat.json'],
    'applearchive_scope': 'C/Swift file streams and Swift flags only; archive coding/decompression explicitly unsupported.',
    'full_xcode_build_ready': probes['full_xcode_build_ready'],
    'signing_ready': False,
    'darling_codesign_stub_bypassed': True,
    'full_build_blocker_log': probes['probes']['xcode-project-build']['log'],
    'full_build_probe_time': probes['checked_at'],
    'probes_report': 'artifacts/xcode-probes.json',
    'experimental_framework_reports': [str(report.relative_to(project)) for report in
        (project/'artifacts/coreml-experiment.json',project/'artifacts/coreml-code-table-audit.json',
         project/'artifacts/collections-metadata-compat.json',project/'artifacts/apfs-fletcher-compat.json',
         project/'artifacts/applekeystore-string-compat.json',project/'artifacts/swift-dispatch-compat.json',
         project/'artifacts/dispatch-executor-compat.json',project/'artifacts/native-symbol-audit.json',
         project/'artifacts/native-string-constants-compat.json',project/'artifacts/constant-float-compat.json',
         project/'artifacts/person-name-compat.json',project/'artifacts/metal-descriptor-compat.json',
         project/'artifacts/person-name-formatter-compat.json',project/'artifacts/mach-port-compat.json',
         project/'artifacts/foundation-xpc-exports.json',project/'artifacts/xpc-send-once-compat.json',
         project/'artifacts/native-accelerate-cpu-compat.json')
        if report.is_file()],
})
assert data['host_smoke_diff_bytes'] == 0
path.write_text(json.dumps(data, indent=2)+'\n')
print('Recorded validated environment and unmodified Apple binary hashes.')
