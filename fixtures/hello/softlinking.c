#include <assert.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
extern void *_sl_dlopen(const char *const *, char **);
extern void *_sl_dlopen_audited(const char *const *);
int main(void) {
    const char *paths[] = { "/linuxcode-missing-first.dylib", "/usr/lib/libSystem.B.dylib", NULL };
    void *image = _sl_dlopen(paths, NULL);
    assert(image);
    int (*loaded_getpid)(void) = dlsym(image, "getpid");
    assert(loaded_getpid && loaded_getpid() == getpid());
    const char *bad[] = { "/linuxcode-missing-first.dylib", "/linuxcode-missing-second.dylib", NULL };
    char *error = NULL;
    assert(_sl_dlopen(bad, &error) == NULL);
    assert(error && strstr(error, "linuxcode-missing-first") && strstr(error, "linuxcode-missing-second"));
    free(error);
    const char *relative[] = { "@rpath/Probe.dylib", NULL };
    image = _sl_dlopen_audited(relative);
    assert(image);
    int (*probe)(void) = dlsym(image, "linuxcode_softlinking_probe");
    assert(probe && probe() == 42);
    puts("SOFTLINKING_FALLBACK_ERRORS_CALLER_RPATH_OK");
}
