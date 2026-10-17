#include <CoreFoundation/CoreFoundation.h>
#include <mach/mach_time.h>
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <assert.h>

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    void *image = dlopen(argv[1], RTLD_LAZY | RTLD_LOCAL);
    if (!image) { fprintf(stderr, "%s\n", dlerror()); return 1; }
    uint64_t (*threshold)(void) = dlsym(image, "SPHIDResponseDelayThreshold");
    assert(threshold && dlsym(image, "SPGenerateSpindump"));
    mach_timebase_info_data_t timebase;
    assert(mach_timebase_info(&timebase) == KERN_SUCCESS && timebase.numer && timebase.denom);
    uint64_t expected = (uint64_t)((__uint128_t)500000000 * timebase.denom / timebase.numer);
    uint64_t actual = threshold();
    printf("SP_THRESHOLD actual=%llu expected=%llu\n", (unsigned long long)actual, (unsigned long long)expected);
    assert(actual == expected && threshold() == actual);
    puts("ORIGINAL_SPINDUMP_THRESHOLD_INITIALIZATION_OK");
}
