#include <CoreGraphics/CGDisplayConfiguration.h>
#include <CoreGraphics/CGError.h>
#include <IOKit/IOKitLib.h>
#include <assert.h>
#include <dlfcn.h>
#include <mach/mach.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

typedef CGError (*Query)(CGDirectDisplayID, io_service_t *, uint32_t *);
static mach_port_t framebuffers[8], devices[8];
static atomic_uint queries[8], display_calls, releases;
static Query query;

static void retain_port(mach_port_t port) {
    assert(mach_port_mod_refs(mach_task_self(), port, MACH_PORT_RIGHT_SEND, 1) == KERN_SUCCESS);
}
static unsigned refs(mach_port_t port) {
    mach_port_urefs_t value = 0;
    assert(mach_port_get_refs(mach_task_self(), port, MACH_PORT_RIGHT_SEND, &value) == KERN_SUCCESS);
    return value;
}
io_service_t fixture_display(CGDirectDisplayID display) {
    atomic_fetch_add(&display_calls, 1);
    if (display == 9) display = 1; // A second display alias for the same service.
    if (display == 7) return MACH_PORT_DEAD;
    if (display == 0 || display >= 8) return MACH_PORT_NULL;
    retain_port(framebuffers[display]);
    return framebuffers[display];
}
IOReturn fixture_accelerator(io_service_t framebuffer, io_service_t *device, uint32_t *index) {
    unsigned display = 1;
    for (; display < 8 && framebuffers[display] != framebuffer; ++display) {}
    assert(display < 8);
    atomic_fetch_add(&queries[display], 1);
    *device = MACH_PORT_NULL;
    *index = 0;
    if (display == 2) return kIOReturnUnsupported;
    if (display == 4) return kIOReturnSuccess; // A success code without a device is insufficient.
    retain_port(devices[display]);
    *device = devices[display];
    *index = display == 5 ? UINT32_MAX : display + 12;
    return display == 3 ? kIOReturnError : kIOReturnSuccess;
}
kern_return_t fixture_release(io_object_t port) {
    atomic_fetch_add(&releases, 1);
    return mach_port_deallocate(mach_task_self(), port);
}
static mach_port_t make_port(void) {
    mach_port_t port;
    assert(mach_port_allocate(mach_task_self(), MACH_PORT_RIGHT_RECEIVE, &port) == KERN_SUCCESS);
    assert(mach_port_insert_right(mach_task_self(), port, port, MACH_MSG_TYPE_MAKE_SEND) == KERN_SUCCESS);
    return port;
}
static void check(unsigned display, bool success) {
    io_service_t device = 0x12345678;
    uint32_t index = 0x12345678;
    CGError result = query(display, &device, &index);
    assert(result == (success ? kCGErrorSuccess : kCGErrorFailure));
    if (!success) { assert(device == MACH_PORT_NULL && index == 0); return; }
    if (display == 9) display = 1;
    assert(device == devices[display]);
    assert(index == (display == 5 ? UINT32_MAX : display + 12));
}
static void *worker(void *unused) {
    for (unsigned i = 0; i < 64; ++i) check(6, true);
    return NULL;
}
int main(int argc, char **argv) {
    assert(argc == 2);
    void *library = dlopen(argv[1], RTLD_LAZY | RTLD_LOCAL);
    if (!library) { fprintf(stderr, "%s\n", dlerror()); return 2; }
    query = (Query)dlsym(library, "CGSAcceleratorForDisplayNumber");
    assert(query);
    for (unsigned i = 1; i < 8; ++i) {
        framebuffers[i] = make_port(); devices[i] = make_port();
    }
    for (unsigned i = 0; i < 8; ++i) check(i, i == 1 || i == 5 || i == 6);
    for (unsigned i = 0; i < 100; ++i) check(i % 2 ? 1 : 9, true);
    for (unsigned i = 1; i < 8; ++i) assert(atomic_load(&queries[i]) == (i == 7 ? 0 : 1));
    unsigned calls = atomic_load(&display_calls);
    io_service_t device = 77;
    uint32_t index = 77;
    assert(query(1, NULL, &index) == kCGErrorIllegalArgument && index == 0);
    assert(query(1, &device, NULL) == kCGErrorIllegalArgument && device == 0);
    assert(query(1, NULL, NULL) == kCGErrorIllegalArgument);
    assert(atomic_load(&display_calls) == calls);
    pthread_t threads[16];
    for (unsigned i = 0; i < 16; ++i) assert(!pthread_create(&threads[i], NULL, worker, NULL));
    for (unsigned i = 0; i < 16; ++i) assert(!pthread_join(threads[i], NULL));
    assert(atomic_load(&queries[6]) == 1);
    for (unsigned i = 1; i < 8; ++i) {
        bool cached = i == 1 || i == 5 || i == 6;
        assert(refs(framebuffers[i]) == (cached ? 2 : 1));
        assert(refs(devices[i]) == (cached ? 2 : 1));
    }
    assert(!dlclose(library));
    for (unsigned i = 1; i < 8; ++i) {
        assert(refs(framebuffers[i]) == 1 && refs(devices[i]) == 1);
        assert(mach_port_destroy(mach_task_self(), framebuffers[i]) == KERN_SUCCESS);
        assert(mach_port_destroy(mach_task_self(), devices[i]) == KERN_SUCCESS);
    }
    puts("CGS_ACCELERATOR_SOURCE_BORROWED_CACHE_ERRORS_ALIASES_1024_CONCURRENT_QUERIES_UNLOAD_REAL_PORT_REFS_OK");
    return 0;
}
