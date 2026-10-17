#include <assert.h>
#include <stdbool.h>
#include <dlfcn.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>

typedef bool (*feature_fn)(const char *, const char *);
typedef bool (*simple_fn)(const char *, const char *, bool);
static feature_fn bridge_feature, direct_feature;
static simple_fn bridge_simple, direct_simple;
static const char domain[] = "DarlingMissingDomainForNativeFlagTest";
static const char name[] = "DarlingMissingFeatureForNativeFlagTest";
static void check(void) {
    assert(!direct_feature(domain, name));
    assert(bridge_feature(domain, name) == direct_feature(domain, name));
    for (unsigned value = 0; value < 2; value++) {
        assert(direct_simple(domain, name, value) == (bool)value);
        assert(bridge_simple(domain, name, value) == direct_simple(domain, name, value));
    }
}
static void *worker(void *unused) { for (unsigned i = 0; i < 64; i++) check(); return NULL; }
int main(int argc, char **argv) {
    assert(argc == 3);
    setbuf(stdout, NULL);
    puts("NATIVE_FEATUREFLAGS_MAIN_ENTERED");
    void *system = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    assert(system);
    bridge_feature = (feature_fn)dlsym(system, "_os_feature_enabled_impl");
    bridge_simple = (simple_fn)dlsym(system, "_os_feature_enabled_simple_impl");
    assert(bridge_feature && bridge_simple);
    // Invoke the lazy loader before opening the direct provider.
    assert(!bridge_feature(domain, name));
    void *native = dlopen(argv[2], RTLD_LAZY | RTLD_LOCAL);
    assert(native);
    direct_feature = (feature_fn)dlsym(native, "_os_feature_enabled_impl");
    direct_simple = (simple_fn)dlsym(native, "_os_feature_enabled_simple_impl");
    assert(direct_feature && direct_simple && direct_feature != bridge_feature);
    Dl_info owner;
    assert(dladdr((void *)direct_feature, &owner) && !strcmp(owner.dli_fname, argv[2]));
    assert(dladdr((void *)bridge_feature, &owner) && strstr(owner.dli_fname, "libDarlingFeatureFlags.dylib"));
    check();
    pthread_t threads[4];
    for (unsigned i = 0; i < 4; i++) assert(!pthread_create(&threads[i], NULL, worker, NULL));
    for (unsigned i = 0; i < 4; i++) assert(!pthread_join(threads[i], NULL));
    puts("NATIVE_FEATUREFLAGS_REAL_OWNER_MISSING_DOMAIN_BOTH_DEFAULTS_AND_FOUR_THREADS_OK");
    return 0;
}
