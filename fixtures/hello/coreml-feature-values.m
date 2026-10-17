#import <CoreML/MLFeatureValue.h>
#import <Foundation/Foundation.h>
#import <objc/runtime.h>
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define REQUIRE(condition) do { if (!(condition)) { \
    fprintf(stderr, "CoreML check failed at line %d: %s\n", __LINE__, #condition); return 1; \
} } while (0)

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    @autoreleasepool {
        void *library = dlopen(argv[1], RTLD_LAZY | RTLD_LOCAL);
        if (!library) { fprintf(stderr, "%s\n", dlerror()); return 1; }
        Class valueClass = objc_getClass("MLFeatureValue");
        REQUIRE(valueClass != Nil);
        Method factory = class_getClassMethod(valueClass, @selector(featureValueWithInt64:));
        REQUIRE(factory != NULL);
        Dl_info owner;
        REQUIRE(dladdr((void *)method_getImplementation(factory), &owner));
        REQUIRE(strstr(owner.dli_fname, "CoreML.framework") != NULL);
        MLFeatureValue *minimum = [valueClass featureValueWithInt64:INT64_MIN];
        MLFeatureValue *maximum = [valueClass featureValueWithInt64:INT64_MAX];
        REQUIRE(minimum != nil && maximum != nil);
        REQUIRE(minimum.type == MLFeatureTypeInt64 && !minimum.isUndefined);
        REQUIRE(minimum.int64Value == INT64_MIN && maximum.int64Value == INT64_MAX);
        REQUIRE(![minimum isEqualToFeatureValue:maximum]);
        MLFeatureValue *integer = [valueClass featureValueWithInt64:42];
        MLFeatureValue *floating = [valueClass featureValueWithDouble:42.0];
        REQUIRE(floating.type == MLFeatureTypeDouble && floating.doubleValue == 42.0);
        REQUIRE([integer isEqualToFeatureValue:floating]);
        MLFeatureValue *text = [valueClass featureValueWithString:@"Linux CoreML value"];
        REQUIRE(text.type == MLFeatureTypeString && !text.isUndefined);
        REQUIRE([text.stringValue isEqualToString:@"Linux CoreML value"]);
        REQUIRE(![text isEqualToFeatureValue:integer]);
        MLFeatureValue *missing = [valueClass undefinedFeatureValueWithType:MLFeatureTypeDouble];
        REQUIRE(missing != nil && missing.isUndefined && missing.type == MLFeatureTypeDouble);
        MLFeatureValue *copied = [integer copy];
        REQUIRE(copied.int64Value == 42 && [copied isEqualToFeatureValue:integer]);
    }
    puts("ORIGINAL_COREML_INT64_LIMITS_DOUBLE_STRING_UNDEFINED_EQUALITY_COPY_OK");
    return 0;
}
