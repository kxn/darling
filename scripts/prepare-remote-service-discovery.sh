#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
scripts/prepare-spindump.sh
for target in amsupport fdr remote-service-discovery; do
    python3 scripts/rebuild-c-cache-image.py --target "$target" --modern-adapter --lazy-functions \
        > "logs/rebuild-$target.log" 2>&1
    llvm-objdump-19 --macho --bind --lazy-bind --rebase "runtime/rebuilt-$target/$(
        case "$target" in amsupport) echo libamsupport.dylib;; fdr) echo libFDR.dylib;; *) echo RemoteServiceDiscovery;; esac
    )" > "logs/rebuilt-$target-fixups.log"
    "scripts/test-rebuilt-$target.sh"
done
python3 - <<'PY'
from pathlib import Path
import plistlib,shutil
prefix=Path('runtime/state/prefix')
for target,name in [('amsupport','libamsupport.dylib'),('fdr','libFDR.dylib')]:
    shutil.copyfile(Path('runtime/rebuilt-'+target)/name,prefix/'usr/lib'/name)
root=prefix/'System/Library/PrivateFrameworks/RemoteServiceDiscovery.framework'
(root/'Versions/A/Resources').mkdir(parents=True,exist_ok=True)
shutil.copyfile('runtime/rebuilt-remote-service-discovery/RemoteServiceDiscovery',root/'Versions/A/RemoteServiceDiscovery')
for name,target in [('Versions/Current','A'),('RemoteServiceDiscovery','Versions/Current/RemoteServiceDiscovery'),
    ('Resources','Versions/Current/Resources')]:
    link=root/name
    if not link.exists() and not link.is_symlink():link.symlink_to(target)
(root/'Versions/A/Resources/Info.plist').write_bytes(plistlib.dumps({
    'CFBundleExecutable':'RemoteServiceDiscovery','CFBundleIdentifier':'com.apple.RemoteServiceDiscovery',
    'CFBundlePackageType':'FMWK','LinuxcodeImplementation':'Reconstructed original pinned Intel recovery cache image'}))
PY
workspace=/Volumes/SystemRoot/workspace
for entry in 'amsupport /usr/lib/libamsupport.dylib' 'fdr /usr/lib/libFDR.dylib' \
    'remote-service-discovery /System/Library/PrivateFrameworks/RemoteServiceDiscovery.framework/Versions/A/RemoteServiceDiscovery'; do
    read -r target path <<< "$entry"
    timeout -k 5 30 bin/darling shell "$workspace/artifacts/$target-abi-smoke" "$path" \
        > "logs/$target-installed-execute.log" 2>&1
done
python3 - <<'PY'
from pathlib import Path
import hashlib,json
tests={
    'amsupport':['CFString version value','Base64 encode/decode RFC 4648 known vectors',
        'UInt32 string conversion','two Objective-C classes register their real methods'],
    'fdr':['CoreFoundation type registration','internal tag conversion','internal MD5 known vector'],
    'remote-service-discovery':['seven classes and original protocol registration',
        'actual query init/property copying/mutation/free and wildcard construction',
        'original NSData category SHA256 known vector',
        'missing Security function invocation fails actual dyld lazy binding'],
}
scope={
    'amsupport':'Original library restored with real lazy imports; network/session APIs unverified.',
    'fdr':'Original library restored; device identity, factory-data signing and remote operations unverified.',
    'remote-service-discovery':'Original library restored; device discovery, RemoteXPC and Security chain-copy API unavailable/unverified.',
}
for target in tests:
    report=json.loads(Path('runtime/rebuilt-'+target+'/reconstruction.json').read_text())
    report.pop('patches');report.pop('lazy_binding_slots')
    report.update({'installed':True,'execution_verified':True,'tests':tests[target]+[
        'installed path without loader overrides'], 'scope':scope[target],
        'adapter_sha256':hashlib.sha256(Path('runtime/rebuilt-der/libDarlingDER.dylib').read_bytes()).hexdigest()})
    Path('artifacts/'+target+'-compat.json').write_text(json.dumps(report,indent=2)+'\n')
PY
echo 'Installed original AMSupport/FDR/RemoteServiceDiscovery after real execution tests; remote-device functionality remains unverified.'
