#import <Foundation/Foundation.h>
#include <assert.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

typedef const void *CEError;
typedef CEError (*Serialize)(const void *, CFDictionaryRef, CFDataRef *);
typedef CEError (*Managed)(const void *, CFDataRef, void **);
typedef CEError (*Subset)(void *, void *);
typedef CEError (*Release)(void **);

static void check_image(void *image) {
        const void **runtime = dlsym(image, "CECRuntime");
        CEError *success = dlsym(image, "kCENoError");
        Serialize serialize = dlsym(image, "CESerializeCFDictionary");
        Managed managed = dlsym(image, "CEManagedContextFromCFData");
        Subset subset = dlsym(image, "CEContextIsSubset");
        Release release = dlsym(image, "CEReleaseManagedContext");
        assert(runtime && *runtime && success && *success && serialize && managed && subset && release);
        puts("CE_EXPORTS_OK");
        NSDictionary *dictionaries[] = {
            [NSDictionary dictionaryWithObject:[NSNumber numberWithBool:YES] forKey:@"probe"],
            [NSDictionary dictionaryWithObjectsAndKeys:[NSNumber numberWithBool:YES], @"probe", @"hello", @"extra", nil],
            [NSDictionary dictionaryWithObject:[NSNumber numberWithBool:NO] forKey:@"probe"],
            [NSDictionary dictionaryWithObjectsAndKeys:
                [NSArray arrayWithObjects:@"group.example.one", @"group.example.two", nil], @"groups",
                [NSNumber numberWithInt:7], @"level", [NSNumber numberWithBool:YES], @"probe", nil]
        };
        void *contexts[4] = {NULL, NULL, NULL, NULL};
        CFDataRef encodedData[4] = {NULL, NULL, NULL, NULL};
        for (int i = 0; i < 4; ++i) {
            CFDataRef encoded = NULL;
            CEError error = serialize(*runtime, (CFDictionaryRef)dictionaries[i], &encoded);
            printf("CE_SERIALIZE_%d error=%p success=%p\n", i, error, *success);
            assert(error == *success && encoded && CFDataGetLength(encoded) > 0);
            if (i == 0 || i == 3) {
                FILE *file = fopen(i == 0 ? "/Volumes/SystemRoot/workspace/artifacts/coreentitlements-probe.der" :
                    "/Volumes/SystemRoot/workspace/artifacts/coreentitlements-nested.der", "wb");
                assert(file);
                assert(fwrite(CFDataGetBytePtr(encoded), 1, CFDataGetLength(encoded), file) == (size_t)CFDataGetLength(encoded));
                assert(fclose(file) == 0);
            }
            error = managed(*runtime, encoded, &contexts[i]);
            printf("CE_PARSE_%d error=%p context=%p\n", i, error, contexts[i]);
            assert(error == *success && contexts[i]);
            encodedData[i] = encoded;
        }
        assert(subset(contexts[0], contexts[1]) == *success);
        assert(subset(contexts[1], contexts[0]) != *success);
        assert(subset(contexts[0], contexts[2]) != *success);
        assert(subset(contexts[0], contexts[3]) == *success);
        assert(subset(contexts[3], contexts[1]) != *success);
        puts("CE_SUBSET_POSITIVE_NEGATIVE_OK");
        CFIndex validLength = CFDataGetLength(encodedData[0]);
        NSMutableData *invalid = [NSMutableData dataWithBytes:CFDataGetBytePtr(encodedData[0]) length:validLength];
        ((UInt8 *)[invalid mutableBytes])[1] = 0x7f;
        void *badContext = NULL;
        assert(managed(*runtime, (CFDataRef)invalid, &badContext) != *success);
        assert(badContext == NULL);
        CFDataRef truncated = CFDataCreate(NULL, CFDataGetBytePtr(encodedData[0]), validLength - 1);
        assert(managed(*runtime, truncated, &badContext) != *success);
        assert(badContext == NULL);
        CFRelease(truncated);
        const UInt8 duplicate[] = {0x70,0x1d,0x02,0x01,0x01,0xb0,0x18,
            0x30,0x0a,0x0c,0x05,'p','r','o','b','e',0x01,0x01,0xff,
            0x30,0x0a,0x0c,0x05,'p','r','o','b','e',0x01,0x01,0xff};
        CFDataRef duplicates = CFDataCreate(NULL, duplicate, sizeof(duplicate));
        assert(managed(*runtime, duplicates, &badContext) != *success);
        assert(badContext == NULL);
        CFRelease(duplicates);
        puts("CE_MALFORMED_LENGTH_TRUNCATION_DUPLICATE_KEYS_REJECTED");
        for (int i = 0; i < 4; ++i) {
            assert(release(&contexts[i]) == *success);
            assert(contexts[i] == NULL);
            CFRelease(encodedData[i]);
        }
        puts("ORIGINAL_APPLE_COREENTITLEMENTS_SEMANTICS_OK");
}

int main(int argc, char **argv) {
    int force_slide = argc == 3 && strcmp(argv[2], "--slide") == 0;
    if (argc != 2 && !force_slide) return 2;
    setvbuf(stdout, NULL, _IONBF, 0);
    @autoreleasepool {
        void *blocker = NULL;
        if (force_slide) {
            blocker = dlopen("/Volumes/SystemRoot/workspace/runtime/rebuilt-coreentitlements/libCEBlocker.dylib", RTLD_LAZY | RTLD_LOCAL);
            if (!blocker) { fprintf(stderr, "blocker: %s\n", dlerror()); return 1; }
        }
        void *image = dlopen(argv[1], RTLD_LAZY);
        if (!image) { fprintf(stderr, "%s\n", dlerror()); return 1; }
        if (force_slide) {
            void *first = dlsym(blocker, "CESerializeCFDictionary");
            void *second = dlsym(image, "CESerializeCFDictionary");
            Dl_info firstInfo, secondInfo;
            assert(first && second && first != second);
            assert(dladdr(first, &firstInfo) && dladdr(second, &secondInfo));
            assert(firstInfo.dli_fbase != secondInfo.dli_fbase);
            assert((uintptr_t)firstInfo.dli_fbase != 0x7ff906a22000);
            assert((uintptr_t)secondInfo.dli_fbase != 0x7ff906a22000);
            printf("CE_RELOCATION_PROBE first=%p second=%p\n", firstInfo.dli_fbase, secondInfo.dli_fbase);
            puts("CE_SLIDE_APPLIED");
            check_image(blocker);
        }
        check_image(image);
        if (force_slide) puts("CE_TWO_DISTINCT_COPIES_EXECUTED_OK");
    }
}
