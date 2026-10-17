/* Defer the unchanged native protected-directory implementation. In particular,
 * never replace its protection checks or errors with ordinary mkdir success. */
#include <dlfcn.h>
#include <errno.h>
#include <pthread.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
typedef int (*directory_fn)(const char *, mode_t, const char *);
static directory_fn implementation;
static pthread_once_t once = PTHREAD_ONCE_INIT;
static void load_backend(void) {
    const char *path = "/Volumes/SystemRoot/workspace/runtime/foundation-native-library-stage/libDarlingNativeSandbox.dylib";
    void *handle = dlopen(path, RTLD_LAZY | RTLD_LOCAL);
    if (handle) implementation = (directory_fn)dlsym(handle, "rootless_mkdir_datavault");
    Dl_info owner;
    if (!implementation || !dladdr((void *)implementation, &owner) || strcmp(owner.dli_fname, path)) {
        implementation = NULL;
        fputs("Darling: original protected directory backend unavailable or wrong owner\n", stderr);
    }
}
int rootless_mkdir_datavault(const char *path, mode_t mode, const char *storage_class) {
    int saved_error = errno;
    pthread_once(&once, load_backend);
    if (!implementation) { errno = ENOSYS; return -1; }
    errno = saved_error;
    return implementation(path, mode, storage_class);
}
