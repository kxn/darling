#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
python3 scripts/fetch-cocoapods.py > logs/cocoapods-fetch.log 2>&1
bin/darling shell /bin/bash -c '
if test "$(gem --version)" != 3.4.22; then
    gem install --local --no-document /Volumes/SystemRoot/workspace/runtime/gem-offline-cache/rubygems-update-3.4.22.gem || exit
    /usr/local/bin/update_rubygems --no-document || exit
fi
' > logs/rubygems-update.log 2>&1
mkdir -p runtime/state/prefix/Library/Ruby/Site/2.6.0/rubygems/defaults
cp scripts/rubygems-darwin-defaults.rb \
    runtime/state/prefix/Library/Ruby/Site/2.6.0/rubygems/defaults/operating_system.rb
bin/darling shell /usr/bin/ruby /Volumes/SystemRoot/workspace/scripts/install-cocoapods-guest.rb \
    > logs/cocoapods-offline-install.log 2>&1
bin/darling shell /bin/bash -c 'git --version; pod --version; ruby -rffi -rjson -e "puts FFI::VERSION; puts JSON::VERSION"' \
    > logs/cocoapods-version.log 2>&1
echo 'CocoaPods 1.16.2 and native Intel Darwin FFI are installed.'
