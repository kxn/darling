#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
mkdir -p downloads runtime logs
package=downloads/swift-6.3.3-RELEASE-osx.pkg
if [[ ! -f $package ]]; then
    curl -fLsS --retry 3 \
        https://download.swift.org/swift-6.3.3-release/xcode/swift-6.3.3-RELEASE/swift-6.3.3-RELEASE-osx.pkg \
        -o "$package.part"
    mv "$package.part" "$package"
fi
printf '%s  %s\n' ee82e57774d6650f94aa06302435d6f44a055b9411698db8ecb85d9a3bcc91d0 "$package" | sha256sum --check
if [[ ! -f runtime/swift633-extract-extraction.json ]]; then
    python3 scripts/extract-flat-pkg.py "$package" runtime/swift633-extract \
        > logs/extract-swift633.log 2>&1
fi
scripts/install-swift633-runtime.sh > logs/install-swift633-runtime.log 2>&1
