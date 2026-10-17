#import <Foundation/Foundation.h>
#import <objc/runtime.h>
#include <dlfcn.h>
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

// Signatures recovered from the pinned original library's calling sequences:
// allocator, CFData/CFString input, retained output; zero status means success.
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    setbuf(stdout, NULL);
    @autoreleasepool {
        void *image = dlopen(argv[1], RTLD_LAZY | RTLD_LOCAL);
        if (!image) { fprintf(stderr, "%s\n", dlerror()); return 1; }
        int (*encode)(CFAllocatorRef, CFDataRef, CFStringRef *) = dlsym(image, "AMSupportBase64Encode");
        int (*decode)(CFAllocatorRef, CFStringRef, CFDataRef *) = dlsym(image, "AMSupportBase64Decode");
        Boolean (*number)(CFStringRef, uint32_t *) = dlsym(image, "AMSupportCFStringToUInt32");
        CFStringRef (*version)(void) = dlsym(image, "AMSupportGetLibraryVersionString");
        assert(encode && decode && number && version);
        CFStringRef actualVersion = version();
        assert(actualVersion && CFGetTypeID(actualVersion) == CFStringGetTypeID());
        assert(CFStringGetLength(actualVersion) > 0);
        puts("ORIGINAL_AMSUPPORT_VERSION_CFSTRING_OK");
        const char *plain[] = {"f", "fo", "foo", "foobar"};
        const char *base64[] = {"Zg==", "Zm8=", "Zm9v", "Zm9vYmFy"};
        for (unsigned i = 0; i != 4; ++i) {
            CFDataRef input = CFDataCreate(NULL, (const UInt8 *)plain[i], strlen(plain[i]));
            CFStringRef expected = CFStringCreateWithCString(NULL, base64[i], kCFStringEncodingASCII);
            CFStringRef encoded = NULL;
            CFDataRef decoded = NULL;
            assert(encode(NULL, input, &encoded) == 0 && encoded);
            assert(CFEqual(encoded, expected));
            assert(decode(NULL, encoded, &decoded) == 0 && decoded);
            assert(CFEqual(decoded, input));
            CFRelease(input); CFRelease(expected); CFRelease(encoded); CFRelease(decoded);
        }
        puts("ORIGINAL_AMSUPPORT_BASE64_KNOWN_VECTORS_OK");
        uint32_t result = 0;
        assert(number(CFSTR("4294967295"), &result) && result == UINT32_MAX);
        assert(number(CFSTR("42"), &result) && result == 42);
        puts("ORIGINAL_AMSUPPORT_LAZY_BINDING_EXECUTED_OK");
        const char *classes[] = {"AMSupportOSURLConnectionDelegate", "AMSupportOSURLSession"};
        for (unsigned i = 0; i != 2; ++i) {
            Class cls = objc_getClass(classes[i]);
            assert(cls && class_getSuperclass(cls) == [NSObject class]);
            unsigned count = 0;
            Method *methods = class_copyMethodList(cls, &count);
            assert(methods && count > 0);
            for (unsigned j = 0; j < count; ++j) {
                assert(strlen(sel_getName(method_getName(methods[j]))) > 0);
                assert(strlen(method_getTypeEncoding(methods[j])) > 0);
                assert(method_getImplementation(methods[j]));
            }
            printf("OBJC_CLASS %s METHODS %u\n", classes[i], count);
            free(methods);
        }
        puts("ORIGINAL_AMSUPPORT_OBJC_METADATA_REGISTERED_OK");
    }
}
