#!/bin/bash
set -euo pipefail
workspace=/Volumes/SystemRoot/workspace
unset DYLD_FRAMEWORK_PATH
export DYLD_LIBRARY_PATH="$workspace/runtime/rebuilt-apple-archive-original:$workspace/runtime/rebuilt-parallel-compression:$workspace/runtime/rebuilt-compression:$workspace/runtime/rebuilt-der"
aa="$workspace/runtime/recovery-tools/macOS Base System/usr/bin/aa"
output="$workspace/runtime/img4-reference"
destination="$output/payload"
mkdir -p "$destination" "$output/chunks"
for payload_path in "$workspace/runtime/fullsystem/payload-chunks"/payload.0??; do
    if [[ -e "$destination/usr/lib/libimg4.dylib" || -L "$destination/usr/lib/libimg4.dylib" ]]; then exit 0; fi
    part=${payload_path##*/}
    if [[ -f "$output/chunks/$part.done" ]]; then continue; fi
    printf 'IMG4_REFERENCE_SEARCH %s\n' "$part"
    "$aa" convert -i "$payload_path" -o "$output/chunks/$part.aar" \
        -include-path usr/lib/libimg4.dylib -include-path usr/lib/libimage4.dylib \
        -exclude-field uid,gid,mod,flg,mtm,btm,ctm,atm -a raw -t 2 \
        > "$output/chunks/$part.convert.log" 2>&1
    if [[ -s "$output/chunks/$part.aar" ]]; then
        "$aa" extract -i "$output/chunks/$part.aar" -d "$destination" -afsc none -t 2 \
            > "$output/chunks/$part.extract.log" 2>&1
    fi
    touch "$output/chunks/$part.done"
done
[[ -e "$destination/usr/lib/libimg4.dylib" || -L "$destination/usr/lib/libimg4.dylib" ]]
