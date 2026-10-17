// A limited Swift UTI value implementation. The accompanying generated file
// supplies identifiers and conformance edges documented in the installed SDK.
// Objective-C bridging and LaunchServices registration are not implemented.
import Darwin

public enum UTHardwareColor: Hashable, Codable {
    case rgb(UInt8, UInt8, UInt8)
    case indexed(Int32)
}

public struct UTType: Hashable, Codable, CustomStringConvertible, CustomDebugStringConvertible, Sendable {
    public let identifier: String
    internal init(knownIdentifier: String) { identifier = knownIdentifier }
    public init?(_ identifier: String) {
        let canonical = identifier.lowercased()
        guard documentedTypes[canonical] != nil else { return nil }
        self.identifier = canonical
    }
    public var description: String { identifier }
    public var debugDescription: String { "UTType(\(identifier))" }
    // This prefix has no localized LaunchServices type-description database.
    public var localizedDescription: String? { nil }
    public var isDynamic: Bool { identifier.hasPrefix("dyn.") }
    public var isDeclared: Bool { documentedTypes[identifier] != nil }
    public var isPublic: Bool { identifier.hasPrefix("public.") }
    public func conforms(to other: UTType) -> Bool {
        if identifier == other.identifier { return true }
        var pending = documentedTypes[identifier] ?? []
        var visited: Set<String> = []
        while let candidate = pending.popLast() {
            if candidate == other.identifier { return true }
            if visited.insert(candidate).inserted {
                pending += documentedTypes[candidate] ?? []
            }
        }
        return false
    }
    public func isSubtype(of other: UTType) -> Bool { self != other && conforms(to: other) }
    public func isSupertype(of other: UTType) -> Bool { other.isSubtype(of: self) }
    public var supertypes: Set<UTType> {
        Set(documentedTypes.keys.compactMap { key in
            guard let type = UTType(key), type != self, conforms(to: type) else { return nil }
            return type
        })
    }
    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(identifier, forKey: .identifier)
    }
    private enum CodingKeys: String, CodingKey { case identifier }
    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let identifier = try container.decode(String.self, forKey: .identifier)
        guard let type = UTType(identifier) else {
            throw DecodingError.dataCorruptedError(forKey: .identifier, in: container,
                debugDescription: "Type is not in the SDK type database")
        }
        self = type
    }
    public init?(_deviceModelCode: String, enclosureColor: UTHardwareColor?) {
        fputs("linuxcode: Apple device-model UTI lookup is not implemented\n", stderr)
        errno = ENOTSUP
        return nil
    }
}
