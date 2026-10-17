import Foundation
import Darwin

var checks = 0
func expect(_ value: URL, _ expected: String) {
    guard value.absoluteString == expected else {
        fatalError("URL mismatch: \(value.absoluteString), expected \(expected)")
    }
    checks += 1
}
let file = URL(fileURLWithPath: "/tmp/base", isDirectory: false)
expect(file.appending(path: "child", directoryHint: .notDirectory), "file:///tmp/base/child")
expect(file.appending(path: "/child", directoryHint: .isDirectory), "file:///tmp/base/child/")
expect(file.appending(path: "child/", directoryHint: .inferFromPath), "file:///tmp/base/child/")
expect(file.appending(path: "child/", directoryHint: .notDirectory), "file:///tmp/base/child")
expect(file.appending(path: "a b/中", directoryHint: .notDirectory), "file:///tmp/base/a%20b/%E4%B8%AD")
expect(file.appending(path: "child\0\0", directoryHint: .notDirectory), "file:///tmp/base/child")
let substring = "#nested/file".dropFirst()
expect(file.appending(path: substring, directoryHint: .notDirectory), "file:///tmp/base/nested/file")
expect(file.appending(components: "a", "b/c", directoryHint: .notDirectory), "file:///tmp/base/a/b/c")
expect(file.appending(components: "a", "b/c", directoryHint: .isDirectory), "file:///tmp/base/a/b/c/")

let web = URL(string: "https://example.com/api?x=1#frag")!
expect(web.appending(path: "a/b", directoryHint: .notDirectory), "https://example.com/api/a/b?x=1#frag")
expect(web.appending(component: "AC/DC", directoryHint: .notDirectory), "https://example.com/api/AC%2FDC?x=1#frag")
expect(web.appending(component: "x/", directoryHint: .inferFromPath), "https://example.com/api/x%2F?x=1#frag")
expect(web.appending(component: "100%", directoryHint: .notDirectory), "https://example.com/api/100%25?x=1#frag")
expect(web.appending(component: "café", directoryHint: .notDirectory), "https://example.com/api/caf%C3%A9?x=1#frag")
expect(web.appending(components: "artist", "AC/DC", directoryHint: .isDirectory), "https://example.com/api/artist/AC%2FDC/?x=1#frag")

let directory = "/tmp/linuxcode-url-appending-\(getpid())"
let manager = FileManager.default
try manager.createDirectory(atPath: directory, withIntermediateDirectories: false, attributes: nil)
defer { try? manager.removeItem(atPath: directory) }
let base = URL(fileURLWithPath: directory, isDirectory: true)
let before = base.appending(path: "child", directoryHint: .checkFileSystem)
assert(!before.hasDirectoryPath)
try manager.createDirectory(atPath: directory + "/child", withIntermediateDirectories: false, attributes: nil)
let after = base.appending(path: "child", directoryHint: .checkFileSystem)
assert(after.hasDirectoryPath)
let existingFile = directory + "/file"
assert(manager.createFile(atPath: existingFile, contents: Data([1,2,3]), attributes: nil))
assert(!base.appending(path: "file", directoryHint: .checkFileSystem).hasDirectoryPath)
assert(base.appending(path: "missing/", directoryHint: .checkFileSystem).hasDirectoryPath)
checks += 4
print("URL_APPENDING_GENERIC_PATH_COMPONENTS_ENCODING_HINTS_REAL_FILESYSTEM_OK \(checks)")
