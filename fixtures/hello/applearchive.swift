import AppleArchive
import System
import Darwin

let path = FilePath("/tmp/linuxcode-swift-archive-probe")
let output = ArchiveByteStream.fileStream(path: path, mode: .readWrite,
    options: [.create, .truncate], permissions: [.ownerReadWrite])!
let bytes = Array("Archive byte stream".utf8)
let written = try bytes.withUnsafeBytes { try output.write(from: $0) }
precondition(written == bytes.count)
let position = try output.seek(toOffset: 0, relativeTo: .start)
precondition(position == 0)
var result = [UInt8](repeating: 0, count: bytes.count)
let read = try result.withUnsafeMutableBytes { try output.read(into: $0) }
precondition(read == bytes.count && result == bytes)
let flags: ArchiveFlags = [.ignoreOperationNotPermitted, .extractNoAutoSparse]
precondition(flags.rawValue == 33 && flags.contains(.ignoreOperationNotPermitted))
// Unsupported processing must report failure, never a fake decompressed stream.
errno = 0
precondition(ArchiveByteStream.decompressionStream(readingFrom: output) == nil)
precondition(errno == ENOTSUP)
try output.close()
print("SWIFT_APPLEARCHIVE_FILE_STREAM_OK_UNSUPPORTED_DECODE_REJECTED")
