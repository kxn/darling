import Darwin

@inline(never) func captureLeaf(_ input: Int) async -> UInt32 {
    await Task.yield()
    let identifier = linuxcode_stack_async_test()
    precondition(identifier != 0 && input >= 0)
    return identifier
}
@inline(never) func captureParent(_ input: Int) async -> UInt32 {
    let identifier = await captureLeaf(input)
    precondition(input >= 0)
    return identifier
}
@main struct StackProbe {
    static func main() async {
        CommandLine.arguments[1].withCString { linuxcode_stack_setup($0) }
        await withTaskGroup(of: UInt32.self) { group in
            for i in 0..<64 { group.addTask { await captureParent(i) } }
            var identifiers = Set<UInt32>()
            for await identifier in group { identifiers.insert(identifier) }
            precondition(identifiers.count == 64)
        }
        print("APPLE_THREAD_STACK_64_REAL_SWIFT_ASYNC_TASK_IDS_AND_BOUNDED_FRAMES_OK")
    }
}
