// Partial AppleArchive overlay for Darling. File streams and option flags work.
// Archive coding/decompression are deliberately rejected, never reported done.
import Darwin
import System
import LinuxcodeArchiveC

public enum ArchiveError: Error, Hashable { case ioError, invalidValue }

private func unavailable(_ name: String) {
    fputs("linuxcode: AppleArchive \(name) is not implemented\n", stderr)
    errno = ENOTSUP
}

public struct ArchiveFlags: Hashable, OptionSet {
    public var rawValue: UInt64
    public init() { rawValue = 0 }
    public init(rawValue: UInt64) { self.rawValue = rawValue }
    public static let ignoreOperationNotPermitted = Self(rawValue: 1 << 0)
    public static let archiveDeduplicateData = Self(rawValue: 1 << 1)
    public static let replaceAttributes = Self(rawValue: 1 << 3)
    public static let extractNoAutoDeduplicate = Self(rawValue: 1 << 4)
    public static let extractNoAutoSparse = Self(rawValue: 1 << 5)
    public static func verbosity(level: Int) -> Self {
        Self(rawValue: UInt64(max(0, min(3, level))) << 62)
    }
}

public protocol _AAObjectTraits {
    associatedtype AAType
    static func aaDestroy(_ object: AAType?)
}

public class _AAOptionalObjectWrapper<T: _AAObjectTraits> {
    public typealias AAType = T.AAType
    internal var object: AAType?
    internal var owned: Bool
    public init(object aaObject: AAType?, owned aaObjectOwned: Bool) {
        object = aaObject; owned = aaObjectOwned
    }
    deinit { if owned { T.aaDestroy(object) } }
}

public struct _AAByteStreamTraits: _AAObjectTraits {
    public typealias AAType = OpaquePointer
    public static func aaDestroy(_ object: OpaquePointer?) {
        _ = AAByteStreamClose(object.map(UnsafeMutableRawPointer.init))
    }
}

public class ArchiveByteStream: _AAOptionalObjectWrapper<_AAByteStreamTraits> {
    override public init(object aaObject: AAType?, owned aaObjectOwned: Bool) {
        super.init(object: aaObject, owned: aaObjectOwned)
    }
    private var handle: UnsafeMutableRawPointer {
        get throws {
            guard let object else { throw ArchiveError.invalidValue }
            return UnsafeMutableRawPointer(object)
        }
    }
    public func read(into buffer: UnsafeMutableRawBufferPointer) throws -> Int {
        let count = AAByteStreamRead(try handle, buffer.baseAddress, buffer.count)
        guard count >= 0 else { throw ArchiveError.ioError }; return count
    }
    public func read(into buffer: UnsafeMutableRawBufferPointer, atOffset offset: Int64) throws -> Int {
        let count = AAByteStreamPRead(try handle, buffer.baseAddress, buffer.count, offset)
        guard count >= 0 else { throw ArchiveError.ioError }; return count
    }
    public func write(from buffer: UnsafeRawBufferPointer) throws -> Int {
        let count = AAByteStreamWrite(try handle, buffer.baseAddress, buffer.count)
        guard count >= 0 else { throw ArchiveError.ioError }; return count
    }
    public func write(from buffer: UnsafeRawBufferPointer, atOffset offset: Int64) throws -> Int {
        let count = AAByteStreamPWrite(try handle, buffer.baseAddress, buffer.count, offset)
        guard count >= 0 else { throw ArchiveError.ioError }; return count
    }
    public func seek(toOffset offset: Int64, relativeTo origin: FileDescriptor.SeekOrigin) throws -> Int64 {
        let result = AAByteStreamSeek(try handle, offset, origin.rawValue)
        guard result >= 0 else { throw ArchiveError.ioError }; return result
    }
    public func cancel() {
        if let object { AAByteStreamCancel(UnsafeMutableRawPointer(object)) }
    }
    public func close() throws {
        guard let object else { return }
        self.object = nil
        guard AAByteStreamClose(UnsafeMutableRawPointer(object)) == 0 else { throw ArchiveError.ioError }
    }
    public static func fileStream(path: FilePath, mode: FileDescriptor.AccessMode,
                                  options: FileDescriptor.OpenOptions, permissions: FilePermissions) -> ArchiveByteStream? {
        let pointer = path.withCString { AAFileStreamOpenWithPath($0, mode.rawValue | options.rawValue, permissions.rawValue) }
        return pointer.map { ArchiveByteStream(object: OpaquePointer($0), owned: true) }
    }
    public static func fileStream(fd: FileDescriptor, automaticClose: Bool = true) -> ArchiveByteStream? {
        AAFileStreamOpenWithFD(fd.rawValue, automaticClose ? 1 : 0).map {
            ArchiveByteStream(object: OpaquePointer($0), owned: true)
        }
    }
    public static func temporaryFileStream() -> ArchiveByteStream? {
        AATempFileStreamOpen().map { ArchiveByteStream(object: OpaquePointer($0), owned: true) }
    }
    public static func process(readingFrom input: ArchiveByteStream, writingTo output: ArchiveByteStream) throws -> Int64 {
        let count = AAByteStreamProcess(try input.handle, try output.handle)
        guard count >= 0 else { throw ArchiveError.ioError }; return count
    }
    public static func decompressionStream(readingFrom stream: ArchiveByteStream,
                                           flags: ArchiveFlags = [], threadCount: Int = 0) -> ArchiveByteStream? {
        unavailable("decompressionStream"); return nil
    }
}

// Callback types keep their SDK names. Until archive processing exists, no
// header/attribute/XAT object can be manufactured through this implementation.
public class ArchiveHeader {
    private init() {}
    public class EntryAttributes { private init() {} }
    public class EntryXATBlob { private init() {} }
    public class _EntryFilterWrapper { private init() {} }
    public struct EntryMessage: RawRepresentable, Hashable, CustomStringConvertible {
        public var rawValue: UInt32
        public init(rawValue: UInt32) { self.rawValue = rawValue }
        public var description: String { String(rawValue) }
    }
    public struct EntryMessageStatus: RawRepresentable, Hashable, CustomStringConvertible {
        public var rawValue: Int32
        public init(rawValue: Int32) { self.rawValue = rawValue }
        public static let ok = Self(rawValue: 0)
        public static let skip = Self(rawValue: 1)
        public static let cancel = Self(rawValue: -1)
        public var description: String { String(rawValue) }
    }
    public enum EntryFilterData {
        case header(ArchiveHeader), entryAttributes(EntryAttributes), entryXAT(EntryXATBlob)
    }
    public typealias EntryFilter = (EntryMessage, FilePath, EntryFilterData?) -> EntryMessageStatus
}

public struct _AAArchiveStreamTraits: _AAObjectTraits {
    public typealias AAType = OpaquePointer
    public static func aaDestroy(_ object: OpaquePointer?) {
        if object != nil { fatalError("AppleArchive archive stream destruction is not implemented") }
    }
}
public class _AAOptionalObjectWrapperWithFilter<T: _AAObjectTraits> {
    public typealias AAType = T.AAType
    public init(object aaObject: AAType?, owned aaObjectOwned: Bool,
                messageProc filter: ArchiveHeader._EntryFilterWrapper? = nil) {
        precondition(aaObject == nil, "AppleArchive archive object wrapping is not implemented")
    }
}
public class ArchiveStream: _AAOptionalObjectWrapperWithFilter<_AAArchiveStreamTraits> {
    public func close() throws {
        unavailable("ArchiveStream.close"); throw ArchiveError.invalidValue
    }
    public static func decodeStream(readingFrom stream: ArchiveByteStream,
                                     selectUsing filter: ArchiveHeader.EntryFilter? = nil,
                                     flags: ArchiveFlags = [], threadCount: Int = 0) -> ArchiveStream? {
        unavailable("decodeStream"); return nil
    }
    public static func extractStream(extractingTo directory: FilePath,
                                      selectUsing filter: ArchiveHeader.EntryFilter? = nil,
                                      flags: ArchiveFlags = [], threadCount: Int = 0) -> ArchiveStream? {
        unavailable("extractStream"); return nil
    }
    public static func process(readingFrom input: ArchiveStream, writingTo output: ArchiveStream,
                                selectUsing filter: ArchiveHeader.EntryFilter? = nil,
                                flags: ArchiveFlags = [], threadCount: Int = 0) throws -> Int {
        unavailable("ArchiveStream.process"); throw ArchiveError.invalidValue
    }
}
