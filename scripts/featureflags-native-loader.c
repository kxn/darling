/* Defer the original feature-flag backend until libSystem has initialized.
 * Eagerly depending on it creates a libSystem -> objc/XPC initialization cycle.
 * This bridge provides no feature decisions: both calls use the original code.
 */
#include <stdbool.h>
#include <dlfcn.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef bool (*feature_fn)(const char *, const char *);
typedef bool (*simple_fn)(const char *, const char *, bool);
static feature_fn feature;
static simple_fn simple;
static pthread_once_t once = PTHREAD_ONCE_INIT;

static void load_backend(void) {
    const char *path = "/Volumes/SystemRoot/workspace/runtime/uti-runtime-support/libraries/libsystem_featureflags.dylib";
    void *handle = dlopen(path, RTLD_LAZY | RTLD_LOCAL);
    if (!handle) { fprintf(stderr, "Native feature flags load failed: %s\n", dlerror()); abort(); }
    feature = (feature_fn)dlsym(handle, "_os_feature_enabled_impl");
    simple = (simple_fn)dlsym(handle, "_os_feature_enabled_simple_impl");
    Dl_info owner;
    if (!feature || !simple || !dladdr((void *)feature, &owner) || strcmp(owner.dli_fname, path)) {
        fputs("Native feature flags owner/symbol mismatch\n", stderr); abort();
    }
}

bool _os_feature_enabled_impl(const char *domain, const char *name) {
    pthread_once(&once, load_backend);
    return feature(domain, name);
}

bool _os_feature_enabled_simple_impl(const char *domain, const char *name, bool default_value) {
    pthread_once(&once, load_backend);
    return simple(domain, name, default_value);
}
