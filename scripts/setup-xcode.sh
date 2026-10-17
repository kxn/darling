#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
xip=${1:-"$project/Xcode_26.6_Universal.xip"}
if [[ ! -e runtime/.installed ]]; then scripts/bootstrap.sh; fi
if [[ -f runtime/state/host-cpu-haswell.json ]]; then
    python3 scripts/configure-host-cpu.py > logs/configure-host-cpu.log 2>&1
fi
if [[ ! -f runtime/state/prefix/private/etc/passwd ]]; then bin/darling shell uname -a; fi
if [[ ! -d runtime/state/prefix/Applications/Xcode.app ]]; then
    if [[ ! -d runtime/xcode-extract/Xcode.app ]]; then
        python3 scripts/extract-xip.py "$xip" runtime/xcode-extract > logs/extract-xip.log 2>&1
    fi
    bin/import-xcode runtime/xcode-extract/Xcode.app
fi
scripts/apply-runtime-compat.sh
scripts/setup-cocoapods.sh
scripts/smoke.sh
scripts/test-xcode-tools.sh
scripts/test-constant-numbers.sh
scripts/test-swift-runtime.sh
scripts/test-cocoapods.sh
if ! python3 scripts/probe-xcode.py; then
    echo 'Full Xcode compatibility probes remain unsuccessful; see artifacts/xcode-probes.json.'
fi
python3 scripts/record-environment.py
echo 'Runtime and toolchain checks passed. Full Xcode builds require the separately tracked framework compatibility work.'
