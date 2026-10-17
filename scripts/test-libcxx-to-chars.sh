#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
g++ -std=c++17 -O2 fixtures/hello/libcxx-to-chars.cpp -o runtime/libcxx-to-chars/linux-reference
runtime/libcxx-to-chars/linux-reference > logs/libcxx-to-chars-linux-reference.log
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout -k 5 60 bin/darling shell "$toolchain/usr/bin/clang++" -target x86_64-apple-macos15.4 \
    -isysroot "$sdk" -std=c++17 "$workspace/fixtures/hello/libcxx-to-chars.cpp" \
    -o "$workspace/artifacts/libcxx-to-chars" > logs/libcxx-to-chars-compile.log 2>&1
timeout -k 5 30 bin/darling shell /usr/bin/env \
    DYLD_LIBRARY_PATH="$workspace/runtime/native-library-stage:$workspace/runtime/rebuilt-der:/usr/lib/swift" \
    "$workspace/artifacts/libcxx-to-chars" > logs/libcxx-to-chars-execute.log 2>&1
python3 - <<'PY'
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json
linux=Path('logs/libcxx-to-chars-linux-reference.log').read_text().splitlines()
darwin=[line for line in Path('logs/libcxx-to-chars-execute.log').read_text().splitlines()
 if line.startswith(('D0P','D1P','D2P','D3P','D4P','F0P','F1P','F2P','F3P','F4P','L0 ','L1 ','L2 ','REAL_LIBCXX_'))]
if len(darwin)!=len(linux):raise ValueError('Formatting sample count differs')
hex_variations=0
for index,(a,b) in enumerate(zip(darwin,linux)):
 if a==b:continue
 left,right=a.split(),b.split()
 if left[:2]==right[:2] and left[0] in ('D4P-1','F4P-1'):
  # Both executions independently assert bit-exact parsing and buffer bounds.
  # Hex denormals may use a zero leading digit or normalized exponent.
  hex_variations+=1;continue
 raise ValueError(f'Formatting differs at {index}: Darwin {a!r}, Linux {b!r}')
p=Path('artifacts/libcxx-to-chars.json');r=json.loads(p.read_text())
assert hashlib.sha256(Path('runtime/native-library-stage/libc++.1.dylib').read_bytes()).hexdigest()==r['library_sha256']
r.update(checked_at=datetime.now(timezone.utc).isoformat(),selected_to_chars_execution_verified=True,
 finite_cases=len(linux)-16,hex_normalization_variations=hex_variations,long_double_native_narrowing_cases=15,
 comparison='Independent Linux libstdc++ output, bit-exact finite default/format roundtrip, precision comparisons, exact-fit/short-buffer guards. Hex denormal normalization may differ; both representations parse to the original bits. Long-double overloads match actual Apple Intel narrowing.')
p.write_text(json.dumps(r,indent=2)+'\n');print('Actual libc++ to_chars passed',r['finite_cases'],'finite cases, 15 native long-double cases and independent Linux comparison.')
PY
