#import <Foundation/Foundation.h>
#import <CoreFoundation/CoreFoundation.h>
#import <objc/runtime.h>
#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>

// These objects must be emitted by the original Apple clang, not constructed
// by the test. Compile with -Xclang -fobjc-constant-literals.
static NSNumber *const negative=@(-1234567890123LL);
static NSNumber *const positive=@42;
static NSNumber *const maximum=@18446744073709551615ULL;
static NSNumber *const fractionalNumber=@(-3.125);

int main(void) {
    @autoreleasepool {
        assert(strcmp(object_getClassName(negative),"NSConstantIntegerNumber")==0);
        assert(strcmp(object_getClassName(fractionalNumber),"NSConstantDoubleNumber")==0);
        assert([negative isKindOfClass:[NSNumber class]]);
        assert([negative longLongValue]==-1234567890123LL);
        assert([negative doubleValue]==-1234567890123.0);
        assert([positive intValue]==42 && [positive unsignedCharValue]==42);
        assert([maximum unsignedLongLongValue]==ULLONG_MAX);
        assert([maximum doubleValue]>18446744073709549568.0);
        assert([fractionalNumber doubleValue]==-3.125 && [fractionalNumber longLongValue]==-3);
        long long integer=0;
        [negative getValue:&integer size:sizeof(integer)];
        assert(integer==-1234567890123LL);
        double real=0;
        [fractionalNumber getValue:&real size:sizeof(real)];
        assert(real==-3.125);
        BOOL rejected=NO;
        @try { [fractionalNumber getValue:&real size:1]; }
        @catch(NSException *exception) {
            rejected=[[exception name] isEqualToString:NSInvalidArgumentException];
        }
        assert(rejected);
        assert(CFGetTypeID((CFTypeRef)negative)==CFNumberGetTypeID());
        assert(CFNumberGetValue((CFNumberRef)negative,kCFNumberLongLongType,&integer));
        assert(integer==-1234567890123LL);
        assert(CFNumberGetValue((CFNumberRef)fractionalNumber,kCFNumberDoubleType,&real));
        assert(real==-3.125);
        NSNumber *dynamic=[NSNumber numberWithLongLong:-1234567890123LL];
        assert([negative isEqualToNumber:dynamic] && [negative hash]==[dynamic hash]);
        assert([negative compare:positive]==NSOrderedAscending);
        assert([[negative description] isEqualToString:@"-1234567890123"]);
        assert([[fractionalNumber description] isEqualToString:@"-3.125"]);
        NSDictionary *dictionary=[NSDictionary dictionaryWithObject:@"value" forKey:negative];
        assert([[dictionary objectForKey:dynamic] isEqualToString:@"value"]);
        assert([negative copy]==negative && [fractionalNumber copy]==fractionalNumber);
        [negative retain]; [negative release];
        puts("APPLE_CLANG_CONSTANT_NUMBERS_CONVERSIONS_CF_BRIDGE_HASH_DICTIONARY_OK");
    }
}
