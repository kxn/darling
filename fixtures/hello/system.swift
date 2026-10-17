import System

let path = FilePath("/tmp/linuxcode-swift-system-probe")
let fd = try FileDescriptor.open(path, .readWrite, options: [.create, .truncate], permissions: [.ownerReadWrite])
let message = Array("Swift System in Darling".utf8)
try fd.writeAll(message)
let position = try fd.seek(offset: 0, from: .start)
precondition(position == 0)
var result = [UInt8](repeating: 0, count: message.count)
let count = try result.withUnsafeMutableBytes { try fd.read(into: $0) }
precondition(count == message.count && result == message)
try fd.close()
precondition(path.lastComponent?.string == "linuxcode-swift-system-probe")
precondition(FilePath("/tmp/../tmp/test").lexicallyNormalized().string == "/tmp/test")
do {
    _ = try FileDescriptor.open("/linuxcode-intentionally-missing", .readOnly)
    preconditionFailure("Missing path unexpectedly opened")
} catch let error as Errno {
    precondition(error == .noSuchFileOrDirectory)
}
print("SWIFT_SYSTEM_FILEPATH_IO_ERRNO_OK")
