#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
mkdir -p runtime/cryptokit-test runtime/build-cryptokit/Frameworks/CryptoKit.framework/Versions/A
cp runtime/build-cryptokit/CryptoKit runtime/build-cryptokit/Frameworks/CryptoKit.framework/Versions/A/CryptoKit
ln -sfn A runtime/build-cryptokit/Frameworks/CryptoKit.framework/Versions/Current
ln -sfn Versions/Current/CryptoKit runtime/build-cryptokit/Frameworks/CryptoKit.framework/CryptoKit
if [[ ! -f runtime/cryptokit-test/private.pem ]]; then
    openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -out runtime/cryptokit-test/private.pem
fi
openssl pkey -in runtime/cryptokit-test/private.pem -pubout -out runtime/cryptokit-test/public.pem
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
workspace=/Volumes/SystemRoot/workspace
timeout 60 bin/darling shell "$toolchain/usr/bin/swift-frontend" -c \
    "$workspace/fixtures/hello/cryptokit.swift" -target x86_64-apple-macos14.0 -sdk "$sdk" \
    -module-name CryptoKitABISmoke -o "$workspace/artifacts/cryptokit-abi-smoke.o" \
    > logs/cryptokit-client-compile.log 2>&1
timeout 45 bin/darling shell "$toolchain/usr/bin/clang" -target x86_64-apple-macos14.0 \
    -isysroot "$sdk" "$workspace/artifacts/cryptokit-abi-smoke.o" \
    -L/usr/lib/swift -lswiftCore -lswiftSwiftOnoneSupport -framework CryptoKit -framework Foundation \
    -Wl,-rpath,/usr/lib/swift -o "$workspace/artifacts/cryptokit-abi-smoke" \
    > logs/cryptokit-client-link.log 2>&1
timeout 30 bin/darling shell /usr/bin/env \
    DYLD_FRAMEWORK_PATH="$workspace/runtime/build-cryptokit/Frameworks" \
    "$workspace/artifacts/cryptokit-abi-smoke" > logs/cryptokit-client-execute.log 2>&1
rg -q '^CRYPTOKIT_P256_AND_SHA256_OK$' logs/cryptokit-client-execute.log
openssl dgst -sha256 -verify runtime/cryptokit-test/public.pem \
    -signature artifacts/cryptokit-signature.der artifacts/cryptokit-message.bin \
    > logs/cryptokit-openssl-verify.log 2>&1
rg -q '^Verified OK$' logs/cryptokit-openssl-verify.log
echo 'Original SDK client: P256 signing, valid/tampered verification and SHA256 passed; OpenSSL independently verified the signature.'
