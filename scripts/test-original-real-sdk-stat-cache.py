#!/usr/bin/env python3
"""Exercise original cache generation/reuse and Clang against the full Apple SDK."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, runpy, subprocess

root = Path(__file__).resolve().parent.parent
module = runpy.run_path(str(root / 'scripts/vchroot-links-runtime-profile.py'))
profile = module['profile']()
build = root / 'runtime/real-sdk-stat-cache-test'
build.mkdir(exist_ok=True)
script = build / 'test.sh'
script.write_text('''#!/bin/bash
set -euo pipefail
work=$(mktemp -d /tmp/original-real-sdk-cache.XXXXXX)
trap 'rm -rf "$work"' EXIT
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk
"$toolchain/clang-stat-cache" -v "$sdk" -o "$work/sdk.cache"
test -s "$work/sdk.cache"
echo ORIGINAL_FULL_SDK_CACHE_GENERATION_OK
"$toolchain/clang-stat-cache" -v "$sdk" -o "$work/sdk.cache" > "$work/reuse.log" 2>&1
cat "$work/reuse.log"
grep -q 'Cache up-to-date' "$work/reuse.log"
echo ORIGINAL_FULL_SDK_CACHE_REUSE_OK
"$toolchain/clang" -arch x86_64 -isysroot "$sdk" -ivfsstatcache "$work/sdk.cache" -fsyntax-only /Volumes/SystemRoot/workspace/fixtures/XcodeSmoke/main.c
echo ORIGINAL_FULL_SDK_CACHE_CLANG_CONSUMER_OK
''')
command = profile['command'][:-2] + ['/bin/bash', '/Volumes/SystemRoot/workspace/' + str(script.relative_to(root))]
command[3] = '240'
log = 'logs/original-real-sdk-stat-cache.log'
with (root / log).open('w') as stream:
    result = subprocess.run(command, cwd=root, env=module['environment'](profile), stdout=stream, stderr=subprocess.STDOUT)
text = (root / log).read_text()
digest = lambda path: hashlib.sha256((root / path).read_bytes()).hexdigest()
tool = 'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang-stat-cache'
record = dict(checked_at=datetime.now(timezone.utc).isoformat(), command=command,
              source_runtime=profile['source_runtime'], script=str(script.relative_to(root)), script_sha256=digest(script),
              original_tool=tool, original_tool_sha256=digest(tool), log=log, log_sha256=digest(log),
              exit_status=result.returncode,
              verified=result.returncode == 0 and all(marker in text for marker in [
                  'ORIGINAL_FULL_SDK_CACHE_GENERATION_OK', 'ORIGINAL_FULL_SDK_CACHE_REUSE_OK', 'ORIGINAL_FULL_SDK_CACHE_CLANG_CONSUMER_OK']),
              original_SDK_modified=False, full_xcode_build_ready=False)
(root / 'artifacts/original-real-sdk-stat-cache-test.json').write_text(json.dumps(record, indent=2) + '\n')
print(text[-5000:], end='')
raise SystemExit(0 if record['verified'] else 1)
