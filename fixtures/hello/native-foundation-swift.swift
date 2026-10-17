import Foundation
import Darwin

func phase(_ text: String) { fputs("NATIVE_FOUNDATION_SWIFT_" + text + "\n", stderr) }
phase("MAIN_ENTERED")
let numbers: [Morphology.GrammaticalNumber] = [.singular, .zero, .plural, .pluralTwo, .pluralFew, .pluralMany]
precondition(Set(numbers).count == 6)
for number in numbers {
    precondition(Morphology.GrammaticalNumber(rawValue: number.rawValue) == number)
}
precondition(String(reflecting: Morphology.GrammaticalNumber.self) == "Foundation.Morphology.GrammaticalNumber")
var morphology = Morphology()
morphology.number = .plural
precondition(morphology.number == .plural)
phase("MORPHOLOGY")
let encoder = JSONEncoder()
let decoder = JSONDecoder()
let encoded = try encoder.encode(numbers)
let decoded = try decoder.decode([Morphology.GrammaticalNumber].self, from: encoded)
precondition(decoded == numbers)
let encodedMorphology = try encoder.encode(morphology)
let decodedMorphology = try decoder.decode(Morphology.self, from: encodedMorphology)
precondition(decodedMorphology.number == .plural)
phase("CODABLE")
var text = AttributedString("hello ")
let suffix = AttributedString("中文")
text.append(suffix)
precondition(String(text.characters) == "hello 中文")
let copy = text
text.append(AttributedString("!"))
precondition(String(copy.characters) == "hello 中文" && String(text.characters) == "hello 中文!")
phase("ATTRIBUTED_STRING")
print("NATIVE_FOUNDATION_SWIFT_ENUM_METADATA_HASH_RAWVALUES_CODABLE_AND_ATTRIBUTED_STRING_OK")
