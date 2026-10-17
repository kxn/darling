/* The original helper owns UID/UUID/path semantics. Defer its larger dependency
 * graph until after libSystem startup; this entry only preserves the Intel ABI.
 */
#include <dlfcn.h>
#include <errno.h>
#include <pthread.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
typedef char *(*directory_fn)(uid_t, int, char *, size_t);
static directory_fn implementation;
static pthread_once_t once = PTHREAD_ONCE_INIT;
static void load_backend(void) {
    const char *path = "/Volumes/SystemRoot/workspace/runtime/foundation-native-library-stage/libDarlingNativeDirHelper.dylib";
    void *handle = dlopen(path, RTLD_LAZY | RTLD_LOCAL);
    if (handle) implementation = (directory_fn)dlsym(handle, "__user_local_dirname");
    Dl_info owner;
    if (!implementation || !dladdr((void *)implementation, &owner) || strcmp(owner.dli_fname, path)) {
        implementation = NULL;
        fputs("Darling: original user directory backend unavailable or wrong owner\n", stderr);
    }
}
char *__user_local_dirname(uid_t uid, int which, char *buffer, size_t size) {
    int saved_error = errno;
    pthread_once(&once, load_backend);
    if (!implementation) { errno = ENOSYS; return NULL; }
    errno = saved_error;
    return implementation(uid, which, buffer, size);
}
