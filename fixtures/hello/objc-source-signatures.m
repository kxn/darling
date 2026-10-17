#import <Foundation/Foundation.h>
#include <objc/runtime.h>
#include <dlfcn.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef struct { long long a, b, c; } LCTriple;
@interface LCInvocationTarget : NSObject
- (int)add:(int)a other:(int)b;
- (double)mix:(double)a other:(double)b;
- (LCTriple)triple:(long long)value;
@end
@implementation LCInvocationTarget
- (int)add:(int)a other:(int)b { return a + b; }
- (double)mix:(double)a other:(double)b { return a * 0.5 + b; }
- (LCTriple)triple:(long long)value { return (LCTriple){value, value + 1, value - 1}; }
@end

int main(void) {
    setbuf(stdout, NULL);
    @autoreleasepool {
        puts("SOURCE_OBJC_NATIVE_SIGNATURE_MAIN_ENTERED");
        Dl_info owner;
        assert(dladdr((void *)object_getClass, &owner));
        assert(strstr(owner.dli_fname, "/runtime/objc-source/libobjc.A.dylib"));
        IMP factory = class_getMethodImplementation(object_getClass([NSMethodSignature class]), @selector(signatureWithObjCTypes:));
        assert(dladdr((void *)factory, &owner));
        assert(strstr(owner.dli_fname, "/CoreFoundation.framework/"));
        uintptr_t *tag_mask = dlsym(RTLD_DEFAULT, "objc_debug_taggedpointer_mask");
        assert(tag_mask && *tag_mask == 1);
        const char *encodings[] = {"v@:", "i@:ii", "d@:dd", "q@:q", "@@:@", "v@:@?", "{LCTriple=qqq}@:q"};
        for (unsigned i = 0; i < sizeof(encodings) / sizeof(encodings[0]); i++) {
            NSMethodSignature *signature = [NSMethodSignature signatureWithObjCTypes:encodings[i]];
            assert(signature && [signature numberOfArguments] >= 2);
            if (i == 0) assert(((uintptr_t)signature & *tag_mask) == *tag_mask);
            assert(!strcmp([signature getArgumentTypeAtIndex:0], "@"));
            assert(!strcmp([signature getArgumentTypeAtIndex:1], ":"));
            assert(object_getClass(signature) && [signature isKindOfClass:[NSMethodSignature class]]);
            id retained = [signature retain];
            assert(retained == signature);
            [retained release];
        }
        puts("SOURCE_OBJC_NATIVE_SIGNATURE_SEVEN_REAL_ENCODINGS_CLASS_AND_RR_OK");
        LCInvocationTarget *target = [LCInvocationTarget new];
        NSMethodSignature *signature = [target methodSignatureForSelector:@selector(add:other:)];
        assert([signature numberOfArguments] == 4 && [signature methodReturnLength] == sizeof(int));
        NSInvocation *invocation = [NSInvocation invocationWithMethodSignature:signature];
        [invocation setSelector:@selector(add:other:)];
        int a = -41, b = 100, sum = 0;
        [invocation setArgument:&a atIndex:2]; [invocation setArgument:&b atIndex:3];
        [invocation invokeWithTarget:target]; [invocation getReturnValue:&sum];
        assert(sum == 59);
        invocation = [NSInvocation invocationWithMethodSignature:[target methodSignatureForSelector:@selector(mix:other:)]];
        [invocation setSelector:@selector(mix:other:)];
        double x = -8.5, y = 16, result = 0;
        [invocation setArgument:&x atIndex:2]; [invocation setArgument:&y atIndex:3];
        [invocation invokeWithTarget:target]; [invocation getReturnValue:&result];
        assert(result == 11.75);
        invocation = [NSInvocation invocationWithMethodSignature:[target methodSignatureForSelector:@selector(triple:)]];
        [invocation setSelector:@selector(triple:)];
        long long value = -123456789;
        LCTriple triple;
        [invocation setArgument:&value atIndex:2];
        [invocation invokeWithTarget:target]; [invocation getReturnValue:&triple];
        assert(triple.a == value && triple.b == value + 1 && triple.c == value - 1);
        [target release];
        puts("SOURCE_OBJC_NATIVE_INVOCATION_INTEGER_DOUBLE_AND_STRUCT_RETURN_OK");
    }
    return 0;
}
