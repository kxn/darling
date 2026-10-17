import AppleArchive
import CryptoKit
import System
import Darwin

@_silgen_name("applearchive_native_owner") func nativeOwner() -> Int32
setbuf(stdout, nil)
precondition(nativeOwner() == 1)

enum ProbeError: Error { case stream, shortWrite, wrongContent, acceptedBadKey }
let base = "/Volumes/SystemRoot/workspace/runtime/applearchive-native/"
func file(_ name: String, writing: Bool) throws -> ArchiveByteStream {
    guard let s = ArchiveByteStream.fileStream(path: FilePath(base + name),
        mode: writing ? .readWrite : .readOnly,
        options: writing ? [.create, .truncate] : [], permissions: [.ownerReadWrite]) else { throw ProbeError.stream }
    return s
}
func write(_ bytes: [UInt8], to s: ArchiveByteStream) throws {
    let n = try bytes.withUnsafeBytes { try s.write(from: $0) }
    guard n == bytes.count else { throw ProbeError.shortWrite }
}
func read(_ s: ArchiveByteStream) throws -> [UInt8] {
    var result = [UInt8](), buffer = [UInt8](repeating: 0, count: 8191)
    while true {
        let n = try buffer.withUnsafeMutableBytes { try s.read(into: $0) }
        if n == 0 { return result }
        precondition(n > 0 && n <= buffer.count && result.count < 1_000_000)
        result.append(contentsOf: buffer.prefix(n))
    }
}
let bytes = (0..<65537).map { UInt8(truncatingIfNeeded: ($0 * 17) ^ ($0 >> 8)) }
for (name, algorithm) in [("none", ArchiveCompression.none), ("zlib", .zlib), ("lz4", .lz4), ("lzfse", .lzfse)] {
    print("NATIVE_ARCHIVE_COMPRESSION_BEGIN", name)
    let sink = try file("compression-" + name, writing: true)
    guard let compressor = ArchiveByteStream.compressionStream(using: algorithm, writingTo: sink, blockSize: 16384, threadCount: 1) else { throw ProbeError.stream }
    try write(bytes, to: compressor)
    try compressor.close()
    try sink.close()
    let source = try file("compression-" + name, writing: false)
    guard let decompressor = ArchiveByteStream.decompressionStream(readingFrom: source, threadCount: 1) else { throw ProbeError.stream }
    let decoded = try read(decompressor)
    guard decoded == bytes else { throw ProbeError.wrongContent }
    try decompressor.close()
    try source.close()
    print("NATIVE_ARCHIVE_COMPRESSION_OK", name, decoded.count)
}
print("NATIVE_ARCHIVE_ENCRYPTION_BEGIN")
let keyBytes = (0..<32).map { UInt8($0) }
let key = SymmetricKey(data: keyBytes)
let context = ArchiveEncryptionContext(profile: .hkdf_sha256_aesctr_hmac__symmetric__none,
    compressionAlgorithm: .zlib, compressionBlockSize: 16384)
try context.setSymmetricKey(key)
let sink = try file("encrypted.aea", writing: true)
guard let encoder = ArchiveByteStream.encryptionStream(writingTo: sink, encryptionContext: context, threadCount: 1) else { throw ProbeError.stream }
try write(bytes, to: encoder)
try encoder.close(updatingContext: context)
try sink.close()
func decrypt(_ key: SymmetricKey) throws -> [UInt8] {
    let source = try file("encrypted.aea", writing: false)
    defer { try? source.close() }
    guard let context = ArchiveEncryptionContext(from: source) else { throw ProbeError.stream }
    try context.setSymmetricKey(key)
    guard let decoder = ArchiveByteStream.decryptionStream(readingFrom: source, encryptionContext: context, threadCount: 1) else { throw ProbeError.stream }
    defer { try? decoder.close() }
    return try read(decoder)
}
let recovered = try decrypt(key)
precondition(recovered == bytes)
print("NATIVE_ARCHIVE_ENCRYPTION_ROUNDTRIP_OK", bytes.count)
var rejected = false
do { _ = try decrypt(SymmetricKey(data: [UInt8](repeating: 255, count: 32))) }
catch { rejected = true; print("NATIVE_ARCHIVE_WRONG_KEY_REJECTED", error) }
precondition(rejected)
guard let damaged = ArchiveByteStream.fileStream(path: FilePath(base + "encrypted.aea"),
    mode: .readWrite, options: [], permissions: [.ownerReadWrite]) else { throw ProbeError.stream }
var original = [UInt8](repeating: 0, count: 1)
let count = try original.withUnsafeMutableBytes { try damaged.read(into: $0, atOffset: 8192) }
precondition(count == 1)
let modified = [original[0] ^ 0x80]
let changed = try modified.withUnsafeBytes { try damaged.write(from: $0, atOffset: 8192) }
precondition(changed == 1)
try damaged.close()
var corruptionRejected = false
do { _ = try decrypt(key) }
catch { corruptionRejected = true; print("NATIVE_ARCHIVE_CORRUPTION_REJECTED", error) }
precondition(corruptionRejected)
print("NATIVE_APPLEARCHIVE_STREAMS_OK")
