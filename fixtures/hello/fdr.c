#include <CoreFoundation/CoreFoundation.h>
#include <dlfcn.h>
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    setbuf(stdout, NULL);
    void *image = dlopen(argv[1], RTLD_LAZY | RTLD_LOCAL);
    if (!image) { fprintf(stderr, "%s\n", dlerror()); return 1; }
    CFTypeID (*type)(void) = dlsym(image, "AMFDRGetTypeID");
    assert(type);
    // These two genuine internal helpers are not public exports. The source
    // image is hash-pinned by the reconstructor; retain their relative offsets.
    Dl_info location;
    assert(dladdr((void *)type, &location) && location.dli_fbase);
    uint32_t (*tag)(const char *) = (void *)((char *)location.dli_fbase + 0x491e);
    Boolean (*digest)(const void *, size_t, unsigned char *) =
        (void *)((char *)location.dli_fbase + 0x2604);
    CFTypeID actual = type();
    assert(actual && actual == type());
    CFStringRef description = CFCopyTypeIDDescription(actual);
    assert(description && CFStringGetLength(description) > 0);
    CFShow(description);
    CFRelease(description);
    puts("ORIGINAL_FDR_CFTYPE_REGISTRATION_OK");
    assert(tag("abcd") == 0x61626364 && tag("0000") == 0x30303030);
    puts("ORIGINAL_FDR_TAG_CONVERSION_OK");
    const unsigned char expected[] = {0x90,0x01,0x50,0x98,0x3c,0xd2,0x4f,0xb0,
        0xd6,0x96,0x3f,0x7d,0x28,0xe1,0x7f,0x72};
    unsigned char result[16];
    memset(result, 0xa5, sizeof(result));
    assert(digest("abc", 3, result));
    assert(memcmp(result, expected, sizeof(result)) == 0);
    puts("ORIGINAL_FDR_MD5_KNOWN_VECTOR_OK");
}
