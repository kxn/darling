#include "thread-stack-async.h"
#include <assert.h>
#include <dlfcn.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef unsigned (*capture_fn)(uintptr_t *,unsigned,unsigned *);
static capture_fn capture;
void linuxcode_stack_setup(const char *path) {
    void *h=dlopen(path,RTLD_NOW|RTLD_LOCAL);
    if (!h) { fputs(dlerror(),stderr);abort(); }
    capture=(capture_fn)dlsym(h,"thread_stack_async_pcs");assert(capture);
    Dl_info owner;assert(dladdr((void *)capture,&owner));
    assert(strstr(owner.dli_fname,"libDarlingFoundationSystem.dylib"));
}
__attribute__((noinline)) static void leaf(void) {
    const uintptr_t guard=UINT64_C(0xaaff001155993377);
    uintptr_t words[66];unsigned count;
    for(unsigned capacity=0;capacity<=64;capacity++) {
        for(unsigned i=0;i<66;i++)words[i]=guard;
        count=999;
        unsigned task=capture(words+1,capacity,&count);
        assert(task==0 && count<=capacity);
        assert(words[0]==guard && words[capacity+1]==guard);
        if(capacity>=16) {
            assert(count>=3);
            uintptr_t expected=(uintptr_t)__builtin_return_address(0);
            unsigned found=0;
            for(unsigned i=0;i<count;i++)if(words[i+1]==expected)found++;
            assert(found==1);
        }
    }
}
__attribute__((noinline)) static void middle(void) { leaf(); __asm__ volatile("" ::: "memory"); }
static void *worker(void *arg) { for(unsigned i=0;i<40;i++)middle();return NULL; }
void linuxcode_stack_ordinary_tests(void) {
    middle();pthread_t threads[4];
    for(unsigned i=0;i<4;i++)assert(!pthread_create(&threads[i],NULL,worker,NULL));
    for(unsigned i=0;i<4;i++)assert(!pthread_join(threads[i],NULL));
    puts("APPLE_THREAD_STACK_ORDINARY_CAPACITY_0_TO_64_AND_FOUR_THREADS_OK");
}
uint32_t linuxcode_stack_async_test(void) {
    void *(*get_task)(void)=(void *(*)(void))dlsym(RTLD_DEFAULT,"swift_task_getCurrent");
    assert(get_task);void *task=get_task();assert(task);
    // The Swift ABI has a static_assert for AsyncTask::Id at this offset.
    uint32_t expected;memcpy(&expected,(char *)task+4*sizeof(void *)+4,sizeof(expected));
    assert(expected);
    assert(pthread_getspecific(103)==task);
    uintptr_t words[66];const uintptr_t guard=UINT64_C(0xaaff001155993377);
    for(unsigned capacity=1;capacity<=64;capacity++) {
        for(unsigned i=0;i<66;i++)words[i]=guard;
        unsigned count=999;
        unsigned actual=capture(words+1,capacity,&count);
        assert(count>0 && count<=capacity && words[0]==guard && words[capacity+1]==guard);
        // Small buffers can fill before reaching the tagged async frame.
        if(capacity==64) { assert(actual==expected);assert(count>=2); }
        for(unsigned i=0;i<count;i++)assert(words[i+1]);
    }
    return expected;
}
#ifndef LINUXCODE_SWIFT_STACK_CLIENT
int main(int argc,char **argv) {
    assert(argc==2);linuxcode_stack_setup(argv[1]);linuxcode_stack_ordinary_tests();return 0;
}
#endif
