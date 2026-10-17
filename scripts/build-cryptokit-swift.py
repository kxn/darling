#!/usr/bin/env python3
"""Build the actual Swift Crypto implementation as a Darwin CryptoKit module.

Uses the original Xcode Swift frontend under Darling. No SDK or Apple executable
is changed. The upstream force-build option enables its BoringSSL backend.
"""
import json
from pathlib import Path
import re
import subprocess

project = Path(__file__).resolve().parent.parent
source = project/'vendor/swift-crypto-3.15.1'
build = project/'runtime/build-cryptokit/swift'
build.mkdir(parents=True, exist_ok=True)
frontend = '/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swift-frontend'
sdk = '/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'

def darwin(path):
    return '/Volumes/SystemRoot/workspace/'+str(path.relative_to(project))

common = ['-c', '-whole-module-optimization', '-parse-as-library', '-Onone',
    '-enable-library-evolution', '-swift-version', '5', '-package-name', 'swift_crypto',
    '-target', 'x86_64-apple-macos14.0', '-sdk', sdk,
    '-D', 'SWIFT_PACKAGE', '-D', 'CRYPTO_IN_SWIFTPM', '-D', 'CRYPTO_IN_SWIFTPM_FORCE_BUILD_API',
    '-I', darwin(source/'Sources/CCryptoBoringSSL/include'),
    '-I', darwin(source/'Sources/CCryptoBoringSSLShims/include'), '-I', darwin(build)]

for module, directory in [('CryptoBoringWrapper', 'CryptoBoringWrapper'), ('CryptoKit', 'Crypto')]:
    inputs = sorted((source/'Sources'/directory).rglob('*.swift'))
    if module == 'CryptoKit':
        # Upstream qualifies a few self references as Crypto.Digest/Crypto.KEM.
        # Swift module aliases reject its inactive `import CryptoKit` branches,
        # so rename only those module qualifications in generated source copies.
        staged = []
        for original in inputs:
            target = build/'CryptoKitSources'/original.relative_to(source/'Sources/Crypto')
            target.parent.mkdir(parents=True, exist_ok=True)
            contents = re.sub(r'\bCrypto\.', 'CryptoKit.', original.read_text())
            # These @usableFromInline backend structs have @inlinable direct
            # initializers. Preserve upstream's fixed internal layout while
            # making the public framework types resilient.
            contents = re.sub(
                r'(?m)^([ \t]*)struct (OpenSSLNISTCurvePublicKeyImpl|OpenSSLCurve25519PublicKeyImpl)(?=[<{ ])',
                r'\1@frozen\n\1struct \2', contents)
            target.write_text(contents)
            staged.append(target)
        inputs = staged
    arguments = [*common, '-module-name', module,
        '-emit-module-path', darwin(build/(module+'.swiftmodule')),
        '-o', darwin(build/(module+'.o')), *map(darwin, inputs)]
    response = build/(module+'.rsp')
    response.write_text('\n'.join(json.dumps(arg) for arg in arguments)+'\n')
    print(f'Compiling {module}: {len(inputs)} Swift files', flush=True)
    with (project/'logs'/('build-cryptokit-'+module+'.log')).open('wb') as log:
        subprocess.run(['timeout', '180', str(project/'bin/darling'), 'shell', frontend,
            '@'+darwin(response)], cwd=project, stdout=log, stderr=subprocess.STDOUT, check=True)
    print(f'Compiled {module}', flush=True)
