// ABI documented in Apple's dyld other-tools/dsc_extractor.cpp.
// Run the original extractor bundled with Xcode under Darling.
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

typedef int (*extractor_fn)(const char*, const char*, void (^)(unsigned, unsigned));
int main(int argc, char** argv) {
    if (argc != 3) {
        fprintf(stderr, "usage: dsc-extract cache-path output-directory\n");
        return 2;
    }
    void* image = dlopen("/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneOS.platform/usr/lib/dsc_extractor.bundle", RTLD_NOW);
    if (!image) {
        fprintf(stderr, "extractor load failed: %s\n", dlerror());
        return 1;
    }
    extractor_fn extract = (extractor_fn)dlsym(image, "dyld_shared_cache_extract_dylibs_progress");
    if (!extract) {
        fprintf(stderr, "extractor symbol missing: %s\n", dlerror());
        return 1;
    }
    if (strcmp(argv[1], "--probe") == 0) {
        puts("Original Xcode shared-cache extractor loaded.");
        return 0;
    }
    int result = extract(argv[1], argv[2], ^(unsigned current, unsigned total) {
        if (current % 100 == 0 || current+1 == total) {
            printf("Extracted %u/%u libraries\n", current+1, total);
            fflush(stdout);
        }
    });
    fprintf(stderr, "Extractor returned %d\n", result);
    return result ? 1 : 0;
}
