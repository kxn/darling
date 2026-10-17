#!/bin/bash
# Run inside Darling. Extract data resources; omit filesystem ownership/flags
# and timestamps that are not supported by the Linux reference directory.
set -euo pipefail
workspace=/Volumes/SystemRoot/workspace
export DYLD_LIBRARY_PATH="$workspace/runtime/rebuilt-apple-archive-original:$workspace/runtime/rebuilt-parallel-compression:$workspace/runtime/rebuilt-compression:$workspace/runtime/rebuilt-der"
aa="$workspace/runtime/recovery-tools/macOS Base System/usr/bin/aa"
output="$workspace/runtime/fullsystem/portable-framework-resources"
destination="$workspace/runtime/fullsystem/framework-resources"
mkdir -p "$output" "$destination"
for payload_path in "$workspace/runtime/fullsystem/payload-chunks"/payload.0??; do
    part=${payload_path##*/}
    if [[ -f "$output/$part.done" ]]; then continue; fi
    "$aa" convert -i "$payload_path" -o "$output/$part.aar" \
        -include-path System/Library/PrivateFrameworks/CoreEmoji.framework \
        -include-path System/Library/Frameworks/NaturalLanguage.framework \
        -include-path System/Library/PrivateFrameworks/LinguisticData.framework \
        -exclude-field uid,gid,mod,flg,mtm,btm,ctm,atm -a raw -t 2 \
        > "$output/$part.convert.log" 2>&1
    if [[ -s "$output/$part.aar" ]]; then
        "$aa" extract -i "$output/$part.aar" -d "$destination" -afsc none -t 2 \
            > "$output/$part.extract.log" 2>&1
    fi
    : > "$output/$part.done"
done
