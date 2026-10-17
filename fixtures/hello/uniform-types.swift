import UniformTypeIdentifiers
import Foundation

precondition(UTType.utf8PlainText.identifier == "public.utf8-plain-text")
precondition(UTType.text.identifier == "public.text")
precondition(UTType("PUBLIC.UTF8-PLAIN-TEXT") == .utf8PlainText)
precondition(UTType.utf8PlainText.conforms(to: .text))
precondition(UTType.utf8PlainText.conforms(to: .data))
precondition(UTType.utf8PlainText.isSubtype(of: .plainText))
precondition(UTType.text.isSupertype(of: .utf8PlainText))
precondition(!UTType.text.conforms(to: .image))
precondition(UTType("org.linuxcode.intentionally-unknown") == nil)
precondition(Set([UTType.text, UTType.text, UTType.utf8PlainText]).count == 2)
let encoded = try JSONEncoder().encode(UTType.utf8PlainText)
let decoded = try JSONDecoder().decode(UTType.self, from: encoded)
precondition(decoded == .utf8PlainText)
print("SWIFT_UTI_IDENTIFIERS_CONFORMANCE_HASH_CODING_OK")
