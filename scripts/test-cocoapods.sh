#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
specs=fixtures/CocoaPodsSmoke/LocalSpecs
if [[ ! -d $specs/.git ]]; then
    git init -q "$specs"
    git -C "$specs" add README.md
    git -C "$specs" -c user.name=Linuxcode -c user.email=linuxcode@example.invalid \
        commit -q -m 'Local CocoaPods test source'
fi
timeout 60 bin/darling shell /bin/bash -c \
    'cd /Volumes/SystemRoot/workspace/fixtures/CocoaPodsSmoke && pod install --no-repo-update' \
    > logs/cocoapods-install-fixture.log 2>&1
rg -q 'Pod installation complete!' logs/cocoapods-install-fixture.log
test -f fixtures/CocoaPodsSmoke/Pods/Pods.xcodeproj/project.pbxproj
test -f fixtures/CocoaPodsSmoke/CocoaPodsSmoke.xcworkspace/contents.xcworkspacedata
timeout 30 bin/darling shell /usr/bin/ruby -rxcodeproj -e \
    'p=Xcodeproj::Project.open(ARGV[0]); abort unless p.targets.any? {|t| t.name=="LocalMath"}; puts "PODS_PROJECT_OK"' \
    /Volumes/SystemRoot/workspace/fixtures/CocoaPodsSmoke/Pods/Pods.xcodeproj \
    > logs/cocoapods-project-verify.log 2>&1
echo 'Darwin CocoaPods installed a local pod and generated a valid workspace and Pods project.'
