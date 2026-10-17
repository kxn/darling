#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
mkdir -p "$project/runtime/state/prefix/usr/bin"
# Darling's shim routes through Xcode's libxcrun and rejects the emulated system.
# Dispatch the original xcodebuild executable using the selected developer dir.
cat > "$project/runtime/state/prefix/usr/bin/xcodebuild" <<'GUEST'
#!/bin/sh
developer_dir=${DEVELOPER_DIR:-}
if [ -z "$developer_dir" ]; then
    developer_dir=$(/usr/bin/xcode-select --print-path) || exit
fi
case "$developer_dir" in
    *.app) developer_dir="$developer_dir/Contents/Developer" ;;
esac
exec "$developer_dir/usr/bin/xcodebuild" "$@"
GUEST
chmod 755 "$project/runtime/state/prefix/usr/bin/xcodebuild"
sed 's@usr/bin/xcodebuild@usr/bin/git@' \
    "$project/runtime/state/prefix/usr/bin/xcodebuild" \
    > "$project/runtime/state/prefix/usr/bin/git"
chmod 755 "$project/runtime/state/prefix/usr/bin/git"
cat > "$project/runtime/state/prefix/usr/bin/codesign" <<'GUEST'
#!/bin/sh
real_codesign='/Volumes/SystemRoot/workspace/runtime/recovery/macOS Base System/usr/bin/codesign'
if [ ! -x "$real_codesign" ]; then
    echo 'codesign: genuine Apple codesign is unavailable in this experimental runtime.' >&2
    exit 69
fi
exec "$real_codesign" "$@"
GUEST
chmod 755 "$project/runtime/state/prefix/usr/bin/codesign"
