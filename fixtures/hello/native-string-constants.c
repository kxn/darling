#include <CoreFoundation/CoreFoundation.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include "../../runtime/native-string-constants/cases.h"

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    void *handle = dlopen(argv[1], RTLD_LAZY | RTLD_LOCAL);
    if (!handle) { fprintf(stderr, "%s\n", dlerror()); return 3; }
    size_t count = sizeof(cases) / sizeof(cases[0]);
    for (size_t i = 0; i < count; ++i) {
        CFStringRef *address = dlsym(handle, cases[i].symbol);
        if (!address || !*address || CFGetTypeID(*address) != CFStringGetTypeID()) return 4;
        CFStringRef expected = CFStringCreateWithCString(NULL, cases[i].value, kCFStringEncodingASCII);
        if (!expected || !CFEqual(*address, expected)) return 5;
        CFMutableStringRef copy = CFStringCreateMutableCopy(NULL, 0, *address);
        if (!copy) return 6;
        CFStringAppend(copy, CFSTR("-independent-copy"));
        if (CFEqual(copy, *address) || !CFEqual(*address, expected)) return 7;
        CFRelease(copy); CFRelease(expected);
    }
    size_t extra_count = sizeof(extra_cases) / sizeof(extra_cases[0]);
    for (size_t i = 0; i < extra_count; ++i) {
        void *address = dlsym(handle, extra_cases[i].symbol);
        if (!address) return 8;
        switch (extra_cases[i].kind) {
            case 1: if (strcmp(*(const char * const *)address, extra_cases[i].string)) return 9; break;
            case 2: if (*(const unsigned int *)address != extra_cases[i].number) return 10; break;
            case 3: if (*(const void * const *)address != address) return 11; break;
            case 4: {
                _Static_assert(sizeof(double) == 8, "Intel CGFloat scalar ABI");
                unsigned long long bits; memcpy(&bits, address, sizeof(bits));
                if (bits != extra_cases[i].bits) return 13;
                break;
            }
            case 5: {
                _Static_assert(sizeof(int) == 4, "CoreImage CIFormat ABI");
                unsigned int bits; memcpy(&bits, address, sizeof(bits));
                if (bits != extra_cases[i].number) return 14;
                break;
            }
            default: return 12;
        }
    }
    printf("ORIGINAL_CFSTRING_IDENTIFIERS_TYPE_EQUALITY_INDEPENDENT_COPY_OK %zu\n", count);
    printf("ORIGINAL_EXTRA_IDENTIFIERS_TYPED_VALUES_OK %zu\n", extra_count);
    return 0;
}
