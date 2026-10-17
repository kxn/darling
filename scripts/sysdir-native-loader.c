/* Keep all three state-machine entries on the same original Intel provider. */
#include <dlfcn.h>
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sysdir.h>
typedef sysdir_search_path_enumeration_state (*start_fn)(sysdir_search_path_directory_t, sysdir_search_path_domain_mask_t);
typedef sysdir_search_path_enumeration_state (*next_fn)(sysdir_search_path_enumeration_state, char *);
static start_fn public_start, private_start;
static next_fn next_path;
static pthread_once_t once = PTHREAD_ONCE_INIT;
static void load_backend(void) {
    const char *path = "/Volumes/SystemRoot/workspace/runtime/foundation-native-library-stage/libDarlingNativeDirHelper.dylib";
    void *handle = dlopen(path, RTLD_LAZY | RTLD_LOCAL);
    public_start = handle ? (start_fn)dlsym(handle, "sysdir_start_search_path_enumeration") : NULL;
    private_start = handle ? (start_fn)dlsym(handle, "sysdir_start_search_path_enumeration_private") : NULL;
    next_path = handle ? (next_fn)dlsym(handle, "sysdir_get_next_search_path_enumeration") : NULL;
    void *entries[] = {(void *)public_start, (void *)private_start, (void *)next_path};
    for (unsigned i = 0; i < 3; i++) {
        Dl_info owner;
        if (!entries[i] || !dladdr(entries[i], &owner) || strcmp(owner.dli_fname, path)) {
            fputs("Darling: required original sysdir provider missing or wrong owner\n", stderr);
            abort();
        }
    }
}
static void prepare(void) { int saved = errno; pthread_once(&once, load_backend); errno = saved; }
sysdir_search_path_enumeration_state sysdir_start_search_path_enumeration(sysdir_search_path_directory_t directory, sysdir_search_path_domain_mask_t mask) {
    prepare(); return public_start(directory, mask);
}
sysdir_search_path_enumeration_state sysdir_start_search_path_enumeration_private(sysdir_search_path_directory_t directory, sysdir_search_path_domain_mask_t mask) {
    prepare(); return private_start(directory, mask);
}
sysdir_search_path_enumeration_state sysdir_get_next_search_path_enumeration(sysdir_search_path_enumeration_state state, char *path) {
    prepare(); return next_path(state, path);
}
