#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
mkdir -p vendor/macrecovery downloads runtime/tools/7zip runtime/recovery logs
revision=81ecf1a7e75c318dfc859ddabe5b91f4af757231
if [[ ! -f vendor/macrecovery/macrecovery.py ]]; then
    curl -fLsS --retry 3 \
        "https://raw.githubusercontent.com/acidanthera/OpenCorePkg/$revision/Utilities/macrecovery/macrecovery.py" \
        -o vendor/macrecovery/macrecovery.py
fi
printf '%s  %s\n' 3023a9b4ca79a5255d93c00f25ab5df37e6f938b729b797d9ecea56184b17aff \
    vendor/macrecovery/macrecovery.py | sha256sum --check
python3 scripts/download-recovery-ranges.py > logs/download-recovery.log 2>&1
package=7zip_25.01+dfsg-1~deb13u2_amd64.deb
if [[ ! -f downloads/$package ]]; then
    (cd downloads && apt-get download 7zip=25.01+dfsg-1~deb13u2)
fi
printf '%s  %s\n' b2cb210bee3be6a10230b38b8645d71846d19364b157f44fd08e1a54cae1652f \
    "downloads/$package" | sha256sum --check
dpkg-deb -x "downloads/$package" runtime/tools/7zip
runtime/tools/7zip/usr/lib/7zip/7z x -y -oruntime/recovery downloads/recovery/BaseSystem.dmg \
    'macOS Base System/System/Library/dyld/*' \
    'macOS Base System/System/Library/CoreServices/SystemVersion.plist' \
    'macOS Base System/usr/bin/codesign' > logs/recovery-selected-extract.log 2>&1
scripts/build-dsc-extract.sh
mkdir -p runtime/recovery-libraries
bin/darling shell /Volumes/SystemRoot/workspace/runtime/tools/dsc-extract \
    '/Volumes/SystemRoot/workspace/runtime/recovery/macOS Base System/System/Library/dyld/dyld_shared_cache_x86_64' \
    /Volumes/SystemRoot/workspace/runtime/recovery-libraries > logs/recovery-dsc-extract.log 2>&1
echo 'Extracted reference images for loader research. They are not standalone runnable libraries and are not installed into Darling.'
