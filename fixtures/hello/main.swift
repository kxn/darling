let names = ["Darling", "Swift", "Linux"]
let numbers = Dictionary(uniqueKeysWithValues: names.enumerated().map { ($1, $0) })
precondition(numbers["Swift"] == 1)
print("SWIFT_RUNTIME_OK", names.joined(separator: "/"))
