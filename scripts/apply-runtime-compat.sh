#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
mkdir -p logs artifacts runtime/compat-backups
test -d runtime/state/prefix/Applications/Xcode.app || {
    echo 'Import the supplied Xcode.app first.' >&2
    exit 1
}
python3 scripts/hydrate-swift-runtime.py > logs/hydrate-swift-runtime.log 2>&1
python3 scripts/fix-libsystem-lock-exports.py > logs/fix-libsystem-lock-exports.log 2>&1
for library in libcxx packagekit trace corecrypto corefoundation foundation swift-core rosetta-native; do
    script=scripts/build-${library}-compat.sh
    if [[ $library == rosetta-native ]]; then script=scripts/build-rosetta-native.sh; fi
    "$script" > "logs/build-${library}-compat.log" 2>&1
done
guest="$project/runtime/rootfs/usr/libexec/darling"
cp runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib/swift-5.5/macosx/libswift_Concurrency.dylib \
    "$guest/usr/lib/swift/libswift_Concurrency.dylib"
python3 scripts/configure-platform-version.py > logs/configure-platform-version.log 2>&1
scripts/configure-xcode-dispatch.sh
scripts/prepare-swift633-runtime.sh
scripts/prepare-swift-system.sh
scripts/prepare-cryptokit.sh
scripts/prepare-combine.sh
scripts/build-applearchive.sh
scripts/build-applearchive-swift.sh
scripts/prepare-uniform-types.sh
scripts/build-osanalytics.sh
scripts/build-softlinking.sh
scripts/prepare-remote-service-discovery.sh
# Reapply already-enabled full-reference modules after rebuilding base wrappers.
# A fresh basic setup does not silently download the separate full installer.
if [[ -f artifacts/core-emoji-compat.json && -f runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h ]]; then
    scripts/prepare-core-emoji.sh
fi
if [[ -f artifacts/swift-os-compat.json && -f runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h ]]; then
    scripts/prepare-swift-os.sh
fi
echo 'Applied isolated Darling runtime compatibility repairs; Xcode binaries remain unchanged.'
