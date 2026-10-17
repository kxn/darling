#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
mkdir -p logs runtime/fullsystem
if [[ -f runtime/fullsystem/intel-system-reference.apfs ]]; then
    python3 scripts/verify-intel-cache-pages.py
    python3 scripts/verify-intel-system-image.py --cache-reference
    exit 0
fi
python3 scripts/download-installassistant.py
if [[ ! -f runtime/fullsystem/SharedSupport.dmg ]]; then
    python3 scripts/extract-xar-member.py downloads/InstallAssistant-25G83.pkg \
        SharedSupport.dmg runtime/fullsystem/SharedSupport.dmg > logs/extract-installassistant-sharedsupport.log 2>&1
fi
zip=runtime/fullsystem/sharedsupport/Shared\ Support/com_apple_MobileAsset_MacSoftwareUpdate/60533a8ae8e47c23593a6965d64c1f00a6396cfe.zip
if [[ ! -f "$zip" ]]; then
    runtime/tools/7zip/usr/lib/7zip/7z x -y -oruntime/fullsystem/sharedsupport \
        runtime/fullsystem/SharedSupport.dmg 'Shared Support/com_apple_MobileAsset_MacSoftwareUpdate/*.zip' \
        > logs/sharedsupport-extract-asset.log 2>&1
fi
runtime/tools/7zip/usr/lib/7zip/7z x -y -oruntime/fullsystem/intel "$zip" \
    AssetData/payloadv2/image_patches/cryptex-system-x86_64 AssetData/boot/BuildManifest.plist \
    > logs/fullsystem-extract-intel-patch.log 2>&1
python3 - <<'PY'
from pathlib import Path
import hashlib,json
manifest=json.loads(Path('config/apple-installer-25G83.json').read_text())
source=Path('runtime/fullsystem/intel/AssetData/payloadv2/image_patches/cryptex-system-x86_64')
with source.open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
if actual!=manifest['intel_patch_sha256']:raise ValueError('Intel RIDIFF patch SHA256 mismatch')
PY
# This initializes the pinned cache readers and shared compatibility adapter.
scripts/prepare-coreentitlements.sh > logs/prepare-coreentitlements.log 2>&1
for target in compression parallel-compression; do
    python3 scripts/rebuild-c-cache-image.py --target "$target" --modern-adapter --lazy-functions \
        > "logs/rebuild-$target.log" 2>&1
done
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout -k 5 45 bin/darling shell "$toolchain/usr/bin/clang" -target x86_64-apple-macos14.0 \
    -isysroot "$sdk" "$workspace/scripts/raw-image-patch.c" -o "$workspace/runtime/tools/raw-image-patch" \
    > logs/raw-image-patch-compile.log 2>&1
if [[ -f runtime/fullsystem/intel-system.dmg.partial ]]; then
    mv runtime/fullsystem/intel-system.dmg.partial "runtime/fullsystem/intel-system.dmg.failed.$(date +%s)"
fi
timeout -k 5 900 bin/darling shell /usr/bin/env \
    DYLD_LIBRARY_PATH="$workspace/runtime/rebuilt-compression:$workspace/runtime/rebuilt-der" \
    "$workspace/runtime/tools/raw-image-patch" \
    "$workspace/runtime/rebuilt-parallel-compression/libParallelCompression.dylib" \
    "$workspace/runtime/fullsystem/intel/AssetData/payloadv2/image_patches/cryptex-system-x86_64" \
    "$workspace/runtime/fullsystem/intel-system.dmg.partial" > logs/raw-image-patch-execute.log 2>&1
rg -q '^RawImagePatch returned 0$' logs/raw-image-patch-execute.log
runtime/tools/7zip/usr/lib/7zip/7z x -y -sns -oruntime/fullsystem/intel-cache-streams \
    runtime/fullsystem/intel-system.dmg.partial \
    'System/Library/dyld/dyld_shared_cache_x86_64h*:com.apple.ResourceFork' \
    'System/Library/dyld/dyld_shared_cache_x86_64h*:com.apple.decmpfs' > logs/intel-cache-stream-extract.log 2>&1
if [[ ! -d vendor/libzbitmap/.git ]]; then
    git init -q vendor/libzbitmap
    git -C vendor/libzbitmap remote add origin https://github.com/eafer/libzbitmap.git
    git -C vendor/libzbitmap fetch --depth 1 origin 574abeae25b25c3319b9b6a9225cc7464e08ae88
    git -C vendor/libzbitmap checkout --detach FETCH_HEAD
fi
python3 scripts/decode-intel-cache-streams.py
python3 scripts/verify-intel-cache-pages.py
python3 scripts/verify-intel-system-image.py --cache-reference --record-runtime-execution
echo 'Intel reference cache contents verified. Whole-image SHA384 discrepancy remains unresolved; this is not a bootable-OS validation.'
