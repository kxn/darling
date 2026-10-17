import Foundation

let message = "Darling Swift Foundation"
let bytes = Data(message.utf8)
precondition(String(data: bytes, encoding: .utf8) == message)
let encoded = try JSONSerialization.data(withJSONObject: ["message": message, "count": bytes.count])
let decoded = try JSONSerialization.jsonObject(with: encoded) as! [String: Any]
precondition(decoded["message"] as? String == message)
print("SWIFT_FOUNDATION_OK", bytes.count)
