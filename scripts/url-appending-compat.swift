// Backport selected URL appending APIs over the existing Foundation backend.
// Semantics reference: pinned swift-foundation URL.swift and URL_Impl.swift.
import Foundation

private func appendAtom(_ base: URL, _ input: String, _ hint: URL.DirectoryHint,
                        component: Bool) -> URL {
    var path = input
    if base.isFileURL {
        while path.last == "\0" { path.removeLast() }
    }
    let encodeSlashes = component && !base.isFileURL
    let isDirectory: Bool
    switch hint {
    case .isDirectory: isDirectory = true
    case .notDirectory: isDirectory = false
    case .inferFromPath: isDirectory = !encodeSlashes && path.hasSuffix("/")
    case .checkFileSystem:
        if base.isFileURL {
            let candidate = base.appendingPathComponent(path, isDirectory: false)
            var directory = ObjCBool(false)
            let exists = FileManager.default.fileExists(atPath: candidate.path, isDirectory: &directory)
            isDirectory = exists ? directory.boolValue : path.hasSuffix("/")
        } else {
            isDirectory = !encodeSlashes && path.hasSuffix("/")
        }
    @unknown default:
        preconditionFailure("Unsupported Foundation URL.DirectoryHint case")
    }
    if !encodeSlashes {
        // The legacy CFURL backend appends a directory slash unconditionally.
        // Modern appending retains existing directory separators, and removes
        // trailing separators when explicitly treating the result as a file.
        if isDirectory {
            if path.hasSuffix("/") { path.removeLast() }
        } else {
            while path.hasSuffix("/") { path.removeLast() }
        }
        return base.appendingPathComponent(path, isDirectory: isDirectory)
    }
    // RFC 3986 pchar, with a literal percent sign escaped as input data.
    // This also avoids the unavailable NSCharacterSet URL-specific factories.
    let punctuation = Array("-._~!$&'()*+,;=:@".utf8)
    let hex = Array("0123456789ABCDEF".utf8)
    var bytes: [UInt8] = []
    for byte in path.utf8 {
        if (byte >= 65 && byte <= 90) || (byte >= 97 && byte <= 122) ||
           (byte >= 48 && byte <= 57) || punctuation.contains(byte) {
            bytes.append(byte)
        } else {
            bytes.append(37); bytes.append(hex[Int(byte >> 4)]); bytes.append(hex[Int(byte & 15)])
        }
    }
    let encoded = String(decoding: bytes, as: UTF8.self)
    // NSURLComponents is not implemented by the existing Darling Foundation.
    // Work on the already escaped absolute URI, retaining its query/fragment.
    let absolute = base.absoluteString
    let split = absolute.firstIndex { $0 == "?" || $0 == "#" } ?? absolute.endIndex
    let suffix = String(absolute[split...])
    var joined = String(absolute[..<split])
    if joined.isEmpty { joined = "." }
    if !joined.hasSuffix("/") { joined += "/" }
    joined += encoded
    if isDirectory && !joined.hasSuffix("/") { joined += "/" }
    return URL(string: joined + suffix) ?? base
}

extension URL {
    @_silgen_name("$s10Foundation3URLV9appending4path13directoryHintACx_AC09DirectoryF0OtSyRzlF")
    public func _darlingAppendingPath<S: StringProtocol>(path: S, directoryHint: URL.DirectoryHint) -> URL {
        return appendAtom(self, String(path), directoryHint, component: false)
    }

    @_silgen_name("$s10Foundation3URLV9appending9component13directoryHintACx_AC09DirectoryF0OtSyRzlF")
    public func _darlingAppendingComponent<S: StringProtocol>(component: S, directoryHint: URL.DirectoryHint) -> URL {
        return appendAtom(self, String(component), directoryHint, component: true)
    }

    @_silgen_name("$s10Foundation3URLV9appending10components13directoryHintACxd_AC09DirectoryF0OtSyRzlF")
    public func _darlingAppendingComponents<S: StringProtocol>(components: S..., directoryHint: URL.DirectoryHint) -> URL {
        precondition(!components.isEmpty, "URL appending requires at least one component")
        var result = self
        for component in components.dropLast() {
            result = appendAtom(result, String(component), .isDirectory, component: true)
        }
        return appendAtom(result, String(components.last!), directoryHint, component: true)
    }
}
