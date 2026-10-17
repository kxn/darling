/* Swift 6.3.3 Runtime/Concurrency.h and ABI/Executor.h, x86_64. */
#include <stdint.h>
typedef struct { uintptr_t identity,implementation; } ExecutorBits;
extern __attribute__((swiftcall)) ExecutorBits swift_task_getCurrentExecutor(void);
__attribute__((swiftcall)) ExecutorBits linuxcode_current_serial_executor(void) {
    return swift_task_getCurrentExecutor();
}
