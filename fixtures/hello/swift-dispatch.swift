import Dispatch
import Darwin

// Swift 6.3.3 Runtime/Concurrency.h, the actual current serial executor.
@_silgen_name("linuxcode_current_serial_executor")
func currentSerialExecutor()->UnownedSerialExecutor

func progress(_ message:String) {
    if getenv("LINUXCODE_DISPATCH_TEST_TRACE") != nil { fputs(message+"\n",stderr) }
}
progress("Dispatch main entered")

final class State: @unchecked Sendable { var total=0 }
let state=State()
let queue=DispatchQueue(label:"linuxcode.original.dispatch")
let key=DispatchSpecificKey<Int>()
queue.setSpecific(key:key,value:73)
precondition(DispatchQueue.getSpecific(key:key)==nil)
precondition(queue.sync { DispatchQueue.getSpecific(key:key) }==73)
progress("Dispatch specific/sync passed")
let group=DispatchGroup()
for number in 1...64 { queue.async(group:group) { [state] in state.total+=number } }
progress("Dispatch async submitted")
let completion=group.wait(timeout:.now()+5)
progress("Dispatch group completion: \(completion), total: \(state.total)")
precondition(completion == .success)
precondition(queue.sync { state.total }==2080)
progress("Dispatch async/group passed")
let semaphore=DispatchSemaphore(value:0)
precondition(semaphore.wait(timeout:.now()) == .timedOut)
semaphore.signal()
precondition(semaphore.wait(timeout:.now()+1) == .success)
progress("Dispatch semaphore timeout passed")
enum ProbeError:Error { case expected }
do {
    let _:Int=try queue.sync { throw ProbeError.expected }
    preconditionFailure("A throwing sync operation unexpectedly returned")
} catch ProbeError.expected {} catch { preconditionFailure("Wrong error") }
let modernQueue=DispatchSerialQueue(label:"linuxcode.original.serial.executor")
precondition(modernQueue.sync { 41+1 }==42)
actor QueueActor {
    nonisolated let queue:DispatchSerialQueue
    nonisolated var unownedExecutor:UnownedSerialExecutor { queue.asUnownedSerialExecutor() }
    var total=0
    init(queue:DispatchSerialQueue) { self.queue=queue }
    func add(_ number:Int) {
        dispatchPrecondition(condition:.onQueue(queue))
        let active=unsafeBitCast(currentSerialExecutor(),to:(UInt,UInt).self)
        let expected=unsafeBitCast(queue.asUnownedSerialExecutor(),to:(UInt,UInt).self)
        precondition(active.0==expected.0 && active.1==expected.1)
        total+=number
    }
    func value()->Int { total }
}
let finished=DispatchSemaphore(value:0)
Task.detached { [modernQueue,finished] in
    let actor=QueueActor(queue:modernQueue)
    for number in 1...64 { await actor.add(number) }
    let result=await actor.value()
    precondition(result==2080)
    finished.signal()
}
precondition(finished.wait(timeout:.now()+10) == .success)
progress("Dispatch custom actor executor passed")
let preferred=DispatchQueue(label:"linuxcode.original.task.executor",attributes:.concurrent)
let preferenceKey=DispatchSpecificKey<Int>()
preferred.setSpecific(key:preferenceKey,value:991)
let preferenceFinished=DispatchSemaphore(value:0)
Task.detached { [preferred,preferenceKey,preferenceFinished] in
    let sum=await withTaskExecutorPreference(preferred) {
        await withTaskGroup(of:Int.self) { group in
            for number in 1...64 {
                group.addTask {
                    await Task.yield()
                    precondition(DispatchQueue.getSpecific(key:preferenceKey)==991)
                    let serial=unsafeBitCast(currentSerialExecutor(),to:(UInt,UInt).self)
                    precondition(serial.0==0 && serial.1==0)
                    withUnsafeCurrentTask { task in
                        precondition(task?.unownedTaskExecutor==preferred.asUnownedTaskExecutor())
                    }
                    return number
                }
            }
            var result=0
            for await number in group { result+=number }
            return result
        }
    }
    precondition(sum==2080)
    preferenceFinished.signal()
}
precondition(preferenceFinished.wait(timeout:.now()+10) == .success)
progress("Dispatch task executor preference passed")
print("ORIGINAL_SWIFT_DISPATCH_QUEUE_SPECIFIC_ASYNC_GROUP_TIMEOUT_THROW_OK")
