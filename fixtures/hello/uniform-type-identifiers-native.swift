import Foundation
import UniformTypeIdentifiers
import Darwin

setbuf(stdout, nil)
print("NATIVE_UTI_SWIFT_MAIN_ENTERED")
let cases: [(UTType, String, String)] = [
    (.plainText, "public.plain-text", "txt"),
    (.png, "public.png", "png"),
    (.json, "public.json", "json"),
    (.pdf, "com.adobe.pdf", "pdf"),
]
for (type, identifier, ext) in cases {
    print("NATIVE_UTI_CASE_BEGIN \(identifier)")
    precondition(type.identifier == identifier)
    print("NATIVE_UTI_IDENTIFIER_OK \(identifier)")
    precondition(type.preferredFilenameExtension == ext)
    print("NATIVE_UTI_PREFERRED_EXTENSION_OK \(identifier) \(ext)")
    let base = URL(fileURLWithPath: "/tmp/darling-uti-report")
    let result = base.appendingPathExtension(for: type)
    precondition(result.path == "/tmp/darling-uti-report." + ext)
    precondition(base.path == "/tmp/darling-uti-report")
    print("NATIVE_UTI_URL_EXTENSION_OK \(identifier) \(result.path)")
}
print("NATIVE_UTI_IDENTIFIERS_PREFERRED_EXTENSIONS_AND_URL_EXTENSIONS_OK")
for (type, identifier, _) in cases {
    precondition(type.conforms(to: .data))
    print("NATIVE_UTI_CONFORMANCE_OK \(identifier)")
}
precondition(UTType(filenameExtension: "png") == .png)
precondition(UTType(mimeType: "application/json") == .json)
print("NATIVE_UTI_TYPED_TAG_CONFORMANCE_AND_URL_EXTENSION_OK")
