#import <dispatch/dispatch.h>
#import <objc/NSObject.h>
#import <objc/runtime.h>
#include <assert.h>
#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>

int main(int argc,char **argv) {
    if (argc!=2) return 2;
    fputs("Dispatch marker: loading compatibility library\n",stderr);
    void *image=dlopen(argv[1],RTLD_LAZY|RTLD_LOCAL);
    if (!image) { fprintf(stderr,"%s\n",dlerror());return 1; }
    fputs("Dispatch marker: library loaded\n",stderr);
    Class marker=objc_getClass("OS_dispatch_queue_serial_executor");
    Class serial=objc_getClass("OS_dispatch_queue_serial");
    assert(marker && serial && class_getSuperclass(serial)==marker);
    assert(class_getSuperclass(marker)==objc_getClass("OS_dispatch_queue"));
    assert(class_getInstanceSize(marker)==sizeof(void *));
    dispatch_queue_t queue=dispatch_queue_create("linuxcode.executor.compat",NULL);
    assert(queue && [(id)queue isKindOfClass:marker]);
    __block unsigned total=0;
    dispatch_sync(queue,^{total=42;});assert(total==42);
    fputs("Dispatch marker: real queue passed\n",stderr);
    dispatch_source_type_t unsupported=dlsym(image,"_dispatch_source_type_exclaves_notification");
    assert(unsupported);errno=0;
    assert(dispatch_source_create(unsupported,0,0,queue)==NULL && errno==ENOTSUP);
    fputs("Dispatch marker: unsupported source rejected\n",stderr);
    dispatch_source_t source=dispatch_source_create(DISPATCH_SOURCE_TYPE_DATA_ADD,0,0,queue);
    dispatch_semaphore_t ready=dispatch_semaphore_create(0);assert(source && ready);
    __block uintptr_t received=0;
    dispatch_source_set_event_handler(source,^{received=dispatch_source_get_data(source);dispatch_semaphore_signal(ready);});
    dispatch_resume(source);dispatch_source_merge_data(source,7);
    assert(dispatch_semaphore_wait(ready,dispatch_time(DISPATCH_TIME_NOW,5*NSEC_PER_SEC))==0);
    assert(received==7);dispatch_source_cancel(source);
    fputs("Dispatch marker: real data event passed\n",stderr);
    dispatch_release(source);dispatch_release(ready);dispatch_release(queue);
    puts("DISPATCH_EXECUTOR_REAL_QUEUE_DATA_EVENT_AND_UNSUPPORTED_EXCLAVES_REJECTION_OK");
    return 0;
}
