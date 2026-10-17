#!/usr/bin/env python3
"""Record actual compatibility probes; nonzero exit means full builds are blocked."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time

project = Path(__file__).resolve().parent.parent
toolchain = '/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin'
darling = str(project / 'bin/darling')
xcodebuild = str(project / 'bin/xcodebuild')
commands = {
    'xcodebuild-version': [xcodebuild, '-version'],
    'xcodebuild-showsdks': [xcodebuild, '-showsdks'],
    'xcode-project-build': [xcodebuild, '-project', 'fixtures/XcodeSmoke/XcodeSmoke.xcodeproj',
        '-target', 'XcodeSmoke', '-configuration', 'Release', 'build', 'CODE_SIGNING_ALLOWED=NO'],
    'swift-version': [darling, 'shell', toolchain+'/swift', '--version'],
    'actool-version': [darling, 'shell', '/Applications/Xcode.app/Contents/Developer/usr/bin/actool', '--version'],
    'apple-codesign-version': [darling, 'shell', '/Volumes/SystemRoot/workspace/runtime/recovery/macOS Base System/usr/bin/codesign', '--version'],
    'codesign-entry': [darling, 'shell', '/usr/bin/codesign', '--version'],
}
results = {}
for name, command in commands.items():
    started = time.monotonic()
    log = project / 'logs' / (name+'.log')
    with log.open('wb') as stream:
        result = subprocess.run(['timeout', '-k', '5', '45', *command], cwd=project, stdout=stream, stderr=subprocess.STDOUT)
    results[name] = {
        'exit_code': result.returncode,
        'seconds': round(time.monotonic()-started, 2),
        'log': str(log.relative_to(project)),
    }
    print(f'{name}: exit {result.returncode}', flush=True)

relative = Path('Contents/Developer/usr/bin/xcodebuild')
installed = project / 'runtime/state/prefix/Applications/Xcode.app' / relative
source = project / 'runtime/xcode-extract/Xcode.app' / relative
original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
installed_hash = hashlib.sha256(installed.read_bytes()).hexdigest()
report = {
    'checked_at': datetime.now(timezone.utc).isoformat(),
    'probes': results,
    'apple_xcodebuild_sha256': installed_hash,
    'apple_xcodebuild_matches_xip_extraction': original_hash == installed_hash,
    'full_xcode_build_ready': results['xcode-project-build']['exit_code'] == 0,
    'signing_ready': False,
    'signing_note': 'The codesign entry forwards to genuine Apple codesign, which lacks its AMFI framework. It does not run Darling\'s success-returning stub. No signed app verified.',
    'cache_extraction_note': 'Raw extraction is analysis-only. Selected hash-pinned images are reconstructed and installed only after semantic tests; see compatibility reports.',
}
(project / 'artifacts/xcode-probes.json').write_text(json.dumps(report, indent=2)+'\n')
raise SystemExit(0 if report['full_xcode_build_ready'] else 1)
