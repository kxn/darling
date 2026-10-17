#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
mkdir -p downloads/debs runtime/rootfs runtime/state runtime/home logs artifacts
fetch() {
    local name=$1 url=$2 checksum=$3
    if [[ ! -f downloads/$name ]]; then
        curl -fLsS --retry 3 -o "downloads/$name.part" "$url"
        mv "downloads/$name.part" "downloads/$name"
    fi
    printf '%s  %s\n' "$checksum" "downloads/$name" | sha256sum --check
}
fetch debs_20260608.zip \
    https://github.com/darlinghq/darling/releases/download/v0.1.20260608/debs_20260608.zip \
    27469ef3932da2e91dd7fb34b70e3628a3e54b7af9fb5480051f44af35eca1fd
fetch ubuntu-base-24.04.5-base-amd64.tar.gz \
    https://cdimage.ubuntu.com/ubuntu-base/releases/24.04/release/ubuntu-base-24.04.5-base-amd64.tar.gz \
    e77b6f10c2590cef872b33ee9f635a0e3fd1f57fb074c0e52b5c7f56147a0c86
unzip -q -o downloads/debs_20260608.zip -d downloads/debs
if [[ ! -x runtime/rootfs/bin/bash ]]; then
    tar --extract --gzip --same-permissions --no-same-owner \
        --file downloads/ubuntu-base-24.04.5-base-amd64.tar.gz \
        --directory runtime/rootfs --exclude='./dev/*'
fi
mkdir -p runtime/rootfs/packages runtime/rootfs/workspace runtime/rootfs/state
sudo unshare --mount --pid --fork --kill-child \
    "$project/scripts/setup-rootfs-ns.sh" "$project/runtime/rootfs" \
    "$project/downloads/debs/debs_20260609" "$(id -u)" "$(id -g)" \
    > "$project/logs/install-rootfs.log" 2>&1
"$project/scripts/build-expat.sh" > "$project/logs/build-expat.log" 2>&1
touch runtime/.installed
"$project/bin/darling" --linux dpkg-query -W > "$project/logs/runtime-packages.txt"
