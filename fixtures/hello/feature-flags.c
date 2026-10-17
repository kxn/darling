#include <assert.h>
#include <stdbool.h>
#include <dlfcn.h>
#include <stdio.h>

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    void *image = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!image) { fprintf(stderr, "%s\n", dlerror()); return 1; }
    bool (*enabled)(const char *, const char *) = dlsym(image, "_os_feature_enabled_impl");
    bool (*simple)(const char *, const char *, bool) = dlsym(image, "_os_feature_enabled_simple_impl");
    assert(enabled && simple);
    assert(!enabled("LinuxcodeCompatibilityTest", "Missing"));
    assert(!simple("LinuxcodeCompatibilityTest", "Missing", false));
    assert(simple("LinuxcodeCompatibilityTest", "Missing", true));
    assert(enabled("LinuxcodeCompatibilityTest", "Enabled"));
    assert(!enabled("LinuxcodeCompatibilityTest", "Disabled"));
    // The original simple API only consults the boot-time shared table.
    // Darling has no featureflags daemon/table; Apple code returns the default.
    assert(!simple("LinuxcodeCompatibilityTest", "Enabled", false));
    assert(simple("LinuxcodeCompatibilityTest", "Disabled", true));
    puts("ORIGINAL_FEATURE_FLAGS_PLIST_AND_DEFAULTS_OK");
}
