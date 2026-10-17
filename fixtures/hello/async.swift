@main struct AsyncSmoke {
    static func main() async {
        let total = await withTaskGroup(of: Int.self) { group in
            for value in 1...8 {
                group.addTask { value }
            }
            var result = 0
            for await value in group { result += value }
            return result
        }
        precondition(total == 36)
        print("SWIFT_CONCURRENCY_OK", total)
    }
}
