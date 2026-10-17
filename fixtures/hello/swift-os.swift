import os

var evaluatedArguments = 0
func logValue() -> Int { evaluatedArguments += 1; return 42 }
func logText() -> String { evaluatedArguments += 1; return "Linux" }

precondition(OSLogType.info.rawValue == 1 && OSLogType.error.rawValue == 16)
let logger = Logger(subsystem: "org.linuxcode.compatibility", category: "runtime-probe")
precondition(logger.isEnabled(type: .default))
precondition(String(reflecting: type(of: logger)).contains("Logger"))
precondition(!Mirror(reflecting: logger).children.isEmpty)
logger.notice("DARLING_ORIGINAL_SWIFT_OS_LOG value \(logValue(), privacy: .public) text \(logText(), privacy: .public)")
precondition(evaluatedArguments == 2)
let levels: Set<OSLogType> = [.info, .debug, .info]
precondition(levels.count == 2 && levels.contains(.debug) && !levels.contains(.error))
let lock = OSAllocatedUnfairLock(initialState: 40)
lock.withLock { $0 += 2 }
precondition(lock.withLock { $0 } == 42)
var destroyed = 0
final class LifetimeProbe { deinit { destroyed += 1 } }
do {
    let objects = OSAllocatedUnfairLock(initialState: [LifetimeProbe()])
    objects.withLock { $0.append(LifetimeProbe()) }
    precondition(objects.withLock { $0.count } == 2)
}
precondition(destroyed == 2)
print("ORIGINAL_SWIFT_OS_LOGGER_INTERPOLATION_REFLECTION_GENERIC_LOCK_OK")
