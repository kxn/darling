/* Portable enqueue transport for the two Swift Dispatch executor entrypoints.
 * Swift 6.3.3 Runtime/Concurrency.h + ABI/Executor.h define the run interfaces.
 * The original Swift Dispatch getters provide the actual witness-table refs. */
#include <dispatch/dispatch.h>
#include <Block.h>
#include <dlfcn.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

typedef struct { void *identity;uintptr_t implementation; } ExecutorRef;
typedef __attribute__((swiftcall)) ExecutorRef ExecutorAccessor(void *self __attribute__((swift_context)));
typedef ExecutorAccessor *GetExecutor;
typedef void (__attribute__((swiftcall)) *RunJob)(void *job,ExecutorRef executor);
static GetExecutor get_serial,get_task;
static RunJob run_serial,run_task;
static pthread_once_t once=PTHREAD_ONCE_INIT;
static void initialize(void) {
    void *overlay=dlopen("/usr/lib/swift/libswiftDispatch.dylib",RTLD_LAZY|RTLD_NOLOAD);
    void *runtime=dlopen("/usr/lib/swift/libswift_Concurrency.dylib",RTLD_LAZY|RTLD_NOLOAD);
    if (!overlay || !runtime) { fputs("dispatch job transport: required runtime is not loaded\n",stderr);abort(); }
    get_serial=(GetExecutor)dlsym(overlay,"$sSo33OS_dispatch_queue_serial_executorC8DispatchE23asUnownedSerialExecutorSceyF");
    get_task=(GetExecutor)dlsym(overlay,"$sSo17OS_dispatch_queueC8DispatchE21asUnownedTaskExecutors0fgH0VyF");
    run_serial=(RunJob)dlsym(runtime,"swift_job_run");
    run_task=(RunJob)dlsym(runtime,"swift_job_run_on_task_executor");
    if (!get_serial || !get_task || !run_serial || !run_task) {
        fputs("dispatch job transport: required genuine executor APIs are missing\n",stderr);abort();
    }
}
static qos_class_t qos(uint32_t priority) {
    /* Swift 6.3.3 MetadataValues.h getPriorityBucketIndex rounding. */
    if (!priority)return QOS_CLASS_UNSPECIFIED;
    if (priority>0x19)return QOS_CLASS_USER_INTERACTIVE;
    if (priority>0x15)return QOS_CLASS_USER_INITIATED;
    if (priority>0x11)return QOS_CLASS_DEFAULT;
    if (priority>0x09)return QOS_CLASS_UTILITY;
    return QOS_CLASS_BACKGROUND;
}
struct Context { dispatch_queue_t queue;void *job;bool task; };
static void execute(struct Context *context) {
    pthread_once(&once,initialize);
    ExecutorRef executor=(context->task?get_task:get_serial)((void *)context->queue);
    if (executor.identity!=(void *)context->queue || !executor.implementation) {
        fputs("dispatch job transport: invalid original executor reference\n",stderr);abort();
    }
    (context->task?run_task:run_serial)(context->job,executor);
    dispatch_release(context->queue);free(context);
}
static void enqueue(dispatch_queue_t queue,void *job,uint32_t priority,bool task) {
    if (!queue || !job)abort();
    struct Context *context=malloc(sizeof(*context));if (!context)abort();
    *context=(struct Context){queue,job,task};dispatch_retain(queue);
    dispatch_block_t block=dispatch_block_create_with_qos_class(0,qos(priority),0,^{execute(context);});
    if (!block) { fputs("dispatch job transport: real QoS work-item construction failed\n",stderr);abort(); }
    dispatch_async(queue,block);Block_release(block);
}
void dispatch_async_swift_job(dispatch_queue_t queue,void *job,uint32_t priority) {
    enqueue(queue,job,priority,false);
}
void darling_dispatch_async_swift_task_job(dispatch_queue_t queue,void *job,uint32_t priority) {
    enqueue(queue,job,priority,true);
}
