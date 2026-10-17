#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" \
    -c fixtures/hello/cache-tls.c -o artifacts/cache-tls-smoke.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 \
    -syslibroot runtime/rootfs/usr/libexec/darling -L runtime/rootfs/usr/libexec/darling/usr/lib \
    -lSystem artifacts/cache-tls-smoke.o -o artifacts/cache-tls-smoke
workspace=/Volumes/SystemRoot/workspace
for target in mecab lexicon; do
    read -r image anchor offset < <(python3 - "$target" <<'PY'
from pathlib import Path
import json,sys
target=sys.argv[1]
report=json.loads(Path('runtime/rebuilt-'+target+'/reconstruction.json').read_text())
descriptor=next(d for d in report['tls_metadata']['descriptors'] if d['zero_fill'] and d['template_offset']==0)
name={'mecab':('libmecab.dylib','mecab_destroy'),'lexicon':('Lexicon','LXAnalyzerCreate')}[target]
print(*name,descriptor['offset'])
PY
    )
    timeout -k 5 30 bin/darling shell /usr/bin/env \
        DYLD_FRAMEWORK_PATH="$workspace/runtime/native-framework-stage" \
        DYLD_LIBRARY_PATH="$workspace/runtime/native-library-stage:$workspace/runtime/rebuilt-der" \
        "$workspace/artifacts/cache-tls-smoke" "$workspace/runtime/rebuilt-$target/$image" "$anchor" "$offset" \
        > "logs/cache-tls-$target-execute.log" 2>&1
    rg -q '^ORIGINAL_CACHE_TLV_THUNK_MAIN_AND_TWO_THREADS_ISOLATED_OK$' "logs/cache-tls-$target-execute.log"
done
echo 'Reconstructed cache TLS templates and descriptors preserve separate main/worker storage in two genuine Apple libraries.'
