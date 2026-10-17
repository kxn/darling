#include "thread-stack-async.h"
#include <assert.h>
#include <dlfcn.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef size_t (*capture_fn)(void **, size_t, uint32_t *);
static capture_fn capture;

void linuxcode_stack_setup(const char *path) {
    void *handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    if (!handle) { fputs(dlerror(), stderr); abort(); }
    capture = (capture_fn)dlsym(handle, "backtrace_async");
    assert(capture);
    Dl_info owner;
    assert(dladdr((void *)capture, &owner));
    assert(strstr(owner.dli_fname, "libDarlingBacktraceAsync.dylib"));
}

__attribute__((noinline)) static void leaf(void) {
    const uintptr_t guard = UINT64_C(0xaaff001155993377);
    uintptr_t words[66];
    for (unsigned capacity = 0; capacity <= 64; capacity++) {
        for (unsigned i = 0; i < 66; i++) words[i] = guard;
        uint32_t task = 999;
        size_t count = capture((void **)(words + 1), capacity, &task);
        assert(task == 0 && count <= capacity);
        assert(words[0] == guard && words[capacity + 1] == guard);
        if (capacity >= 16) {
            assert(count >= 3);
            uintptr_t expected = (uintptr_t)__builtin_return_address(0);
            unsigned found = 0;
            for (unsigned i = 0; i < count; i++) {
                assert(words[i + 1]);
                if (words[i + 1] == expected) found++;
            }
            assert(found == 1);
        }
        count = capture((void **)(words + 1), capacity, NULL);
        assert(count <= capacity && words[0] == guard && words[capacity + 1] == guard);
    }
    uint32_t task = 999;
    assert(capture(NULL, 0, &task) == 0 && task == 0);
    assert(capture(NULL, 0, NULL) == 0);
}

__attribute__((noinline)) static void middle(void) { leaf(); __asm__ volatile("" ::: "memory"); }
static void *worker(void *unused) { for (unsigned i = 0; i < 40; i++) middle(); return NULL; }
void linuxcode_stack_ordinary_tests(void) {
    middle();
    pthread_t threads[4];
    for (unsigned i = 0; i < 4; i++) assert(!pthread_create(&threads[i], NULL, worker, NULL));
    for (unsigned i = 0; i < 4; i++) assert(!pthread_join(threads[i], NULL));
    puts("BACKTRACE_ASYNC_ORDINARY_REAL_PC_CAPACITIES_NULL_OUTPUT_AND_FOUR_THREADS_OK");
}

uint32_t linuxcode_stack_async_test(void) {
    void *(*get_task)(void) = (void *(*)(void))dlsym(RTLD_DEFAULT, "swift_task_getCurrent");
    assert(get_task);
    void *task = get_task();
    assert(task && pthread_getspecific(103) == task);
    uint32_t expected;
    // AsyncTask::Id has this offset in the pinned Swift ABI (also used by Apple).
    memcpy(&expected, (char *)task + 4 * sizeof(void *) + 4, sizeof(expected));
    assert(expected);
    uintptr_t words[66];
    const uintptr_t guard = UINT64_C(0xaaff001155993377);
    for (unsigned capacity = 1; capacity <= 64; capacity++) {
        for (unsigned i = 0; i < 66; i++) words[i] = guard;
        uint32_t actual = 0;
        size_t count = capture((void **)(words + 1), capacity, &actual);
        assert(count > 0 && count <= capacity);
        assert(words[0] == guard && words[capacity + 1] == guard);
        if (capacity == 64) assert(actual == expected && count >= 2);
        for (unsigned i = 0; i < count; i++) assert(words[i + 1]);
    }
    return expected;
}

#ifndef LINUXCODE_SWIFT_STACK_CLIENT
int main(int argc, char **argv) {
    assert(argc == 2);
    linuxcode_stack_setup(argv[1]);
    linuxcode_stack_ordinary_tests();
    return 0;
}
#endif
