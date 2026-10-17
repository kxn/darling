import Foundation
import CryptoKit

// Compile against Xcode's original SDK module, not the implementation's module.
let workspace = "/Volumes/SystemRoot/workspace"
let message = Data("Darling CryptoKit P256 verification".utf8)
let pem = try String(contentsOfFile: workspace + "/runtime/cryptokit-test/private.pem", encoding: .utf8)
let key = try P256.Signing.PrivateKey(pemRepresentation: pem)
let signature = try key.signature(for: message)
precondition(key.publicKey.isValidSignature(signature, for: message))
precondition(!key.publicKey.isValidSignature(signature, for: Data("modified".utf8)))
precondition(signature.rawRepresentation.count == 64)
try signature.derRepresentation.write(to: URL(fileURLWithPath: workspace + "/artifacts/cryptokit-signature.der"))
try message.write(to: URL(fileURLWithPath: workspace + "/artifacts/cryptokit-message.bin"))
let digest = SHA256.hash(data: Data("abc".utf8))
let hex = digest.map { value -> String in
    let digits = String(value, radix: 16)
    return digits.count == 1 ? "0" + digits : digits
}.joined()
precondition(hex == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
print("CRYPTOKIT_P256_AND_SHA256_OK")
