#!/bin/bash
set -euo pipefail
workspace=/Volumes/SystemRoot/workspace
export DYLD_LIBRARY_PATH="$workspace/runtime/rebuilt-apple-archive-original:$workspace/runtime/rebuilt-parallel-compression:$workspace/runtime/rebuilt-compression:$workspace/runtime/rebuilt-der"
aa="$workspace/runtime/recovery-tools/macOS Base System/usr/bin/aa"
output="$workspace/runtime/fullsystem/portable-resource-links"
destination="$workspace/runtime/fullsystem/framework-resources"
first=System/Library/Audio/Tunings/AID25/ADM/config.plist
second=System/Library/LinguisticData/RequiredAssets_ar.bundle/version.plist
mkdir -p "$output" "$destination"
for payload_path in "$workspace/runtime/fullsystem/payload-chunks"/payload.0??; do
    if [[ -f "$destination/$first" && -f "$destination/$second" ]]; then exit 0; fi
    part=${payload_path##*/}
    "$aa" convert -i "$payload_path" -o "$output/$part.aar" \
        -include-path "$first" -include-path "$second" \
        -exclude-field uid,gid,mod,flg,mtm,btm,ctm,atm -a raw -t 2 \
        > "$output/$part.convert.log" 2>&1
    if [[ -s "$output/$part.aar" ]]; then
        "$aa" extract -i "$output/$part.aar" -d "$destination" -afsc none -t 2 \
            > "$output/$part.extract.log" 2>&1
    fi
done
test -f "$destination/$first" && test -f "$destination/$second"
