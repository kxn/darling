#import <Foundation/Foundation.h>
#import <CoreFoundation/CoreFoundation.h>
#import <objc/runtime.h>
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static NSNumber *const negative = @(-3.125f);
static NSNumber *const minusZero = @(-0.0f);
static NSNumber *const maximum = @(0x1.fffffep127f);
static NSNumber *const subnormal = @(0x1p-149f);

int main(void) {
    @autoreleasepool {
        NSNumber *values[] = {negative, minusZero, maximum, subnormal};
        float expected[] = {-3.125f, -0.0f, 0x1.fffffep127f, 0x1p-149f};
        assert([negative floatValue] == -3.125f); // Realize this class before querying objc4 layout.
        Ivar ivar = class_getInstanceVariable(object_getClass(negative), "_value");
        fprintf(stderr, "constant float runtime instance size=%zu, ivar offset=%td\n", class_getInstanceSize(object_getClass(negative)), ivar ? ivar_getOffset(ivar) : -1);
        assert(class_getInstanceSize(object_getClass(negative)) == 16); // objc4 rounds the original 12-byte layout to a word boundary.
        assert(ivar && ivar_getOffset(ivar) == 8 && !strcmp(ivar_getTypeEncoding(ivar), "f"));
        for (size_t i = 0; i < 4; ++i) {
            NSNumber *value = values[i]; float result = 1;
            assert(!strcmp(object_getClassName(value), "NSConstantFloatNumber"));
            assert([value isKindOfClass:[NSNumber class]] && !strcmp([value objCType], "f"));
            [value getValue:&result size:sizeof(result)];
            assert(!memcmp(&result, &expected[i], sizeof(float)));
            assert([value doubleValue] == (double)expected[i]);
            assert(CFGetTypeID((CFTypeRef)value) == CFNumberGetTypeID());
            assert(CFNumberGetValue((CFNumberRef)value, kCFNumberFloatType, &result));
            assert(!memcmp(&result, &expected[i], sizeof(float)));
            NSNumber *dynamic = [NSNumber numberWithFloat:expected[i]];
            assert([value isEqualToNumber:dynamic] && [value hash] == [dynamic hash]);
            NSDictionary *dictionary = [NSDictionary dictionaryWithObject:@"ok" forKey:value];
            assert([[dictionary objectForKey:dynamic] isEqualToString:@"ok"]);
            assert([value copy] == value);
        }
        assert(signbit([minusZero doubleValue]));
        assert([negative longLongValue] == -3);
        BOOL rejected = NO; float output;
        @try { [negative getValue:&output size:1]; }
        @catch (NSException *exception) { rejected = [[exception name] isEqualToString:NSInvalidArgumentException]; }
        assert(rejected);
        puts("APPLE_CLANG_CONSTANT_FLOAT_LAYOUT_BITS_CF_BRIDGE_EQUALITY_HASH_COPY_OK");
    }
}
