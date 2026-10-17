#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
revision=95ba0316a9b733e92bb6b071255ff46263bbe7dc
if [[ ! -d vendor/swift-crypto-3.15.1/.git ]]; then
    git init -q vendor/swift-crypto-3.15.1
    git -C vendor/swift-crypto-3.15.1 remote add origin https://github.com/apple/swift-crypto.git
    git -C vendor/swift-crypto-3.15.1 fetch --depth 1 origin "$revision"
    git -C vendor/swift-crypto-3.15.1 checkout --detach FETCH_HEAD
fi
test "$(git -C vendor/swift-crypto-3.15.1 rev-parse HEAD)" = "$revision"
scripts/build-cryptokit-native.sh > logs/build-cryptokit-native.log 2>&1
python3 scripts/build-cryptokit-swift.py > logs/build-cryptokit-swift.log 2>&1
scripts/link-cryptokit.sh > logs/link-cryptokit.log 2>&1
scripts/test-cryptokit.sh
python3 - <<'PY'
from pathlib import Path
import hashlib, json, plistlib, shutil
root=Path('runtime/state/prefix/System/Library/Frameworks/CryptoKit.framework')
(root/'Versions/A/Resources').mkdir(parents=True,exist_ok=True)
source=Path('runtime/build-cryptokit/CryptoKit')
shutil.copyfile(source,root/'Versions/A/CryptoKit')
(root/'Versions/A/CryptoKit').chmod(0o755)
for name,target in [('Versions/Current','A'),('CryptoKit','Versions/Current/CryptoKit'),('Resources','Versions/Current/Resources')]:
    link=root/name
    if not link.exists() and not link.is_symlink():link.symlink_to(target)
(root/'Versions/A/Resources/Info.plist').write_bytes(plistlib.dumps({
    'CFBundleExecutable':'CryptoKit','CFBundleIdentifier':'com.apple.CryptoKit',
    'CFBundleName':'CryptoKit','CFBundlePackageType':'FMWK','CFBundleShortVersionString':'3.15.1',
    'LinuxcodeImplementation':'Apple swift-crypto 3.15.1 / BoringSSL, built for Darling'}))
Path('artifacts/cryptokit-compat.json').write_text(json.dumps({
    'source_revision':'95ba0316a9b733e92bb6b071255ff46263bbe7dc',
    'framework_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'original_sdk_client_test':'passed', 'p256_sign_verify_and_tamper_test':'passed',
    'sha256_known_vector':'passed','independent_openssl_verification':'passed',
    'scope':'Software CryptoKit APIs from Swift Crypto; full macOS CryptoKit compatibility is not asserted.',
    'loader_mode':'RTLD_LAZY, as used by xcodebuild; strict RTLD_NOW still exposes unrelated legacy CoreGraphics gaps.'
},indent=2)+'\n')
PY
echo 'Installed tested Swift Crypto framework into the isolated Darling prefix.'
