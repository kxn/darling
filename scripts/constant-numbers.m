// ABI verified against the pinned 25G83 Foundation image and its ivar offsets:
// integer { isa, type, value }, double { isa, value }. These are NSNumber
// subclasses; comparison, hashing and CF bridging use the existing runtime.
#import <Foundation/Foundation.h>
#include <string.h>

struct ConstantIntegerNumber { Class isa; const char *type; unsigned long long value; };
struct ConstantDoubleNumber { Class isa; double value; };

#define IMMORTAL_NUMBER \
    - (id)retain { return self; } \
    - (oneway void)release {} \
    - (id)autorelease { return self; } \
    - (NSUInteger)retainCount { return NSUIntegerMax; } \
    - (id)copyWithZone:(NSZone *)zone { return self; }

#define NUMBER_CONVERSIONS \
    - (BOOL)boolValue { return [self doubleValue] != 0; } \
    - (char)charValue { return (char)[self longLongValue]; } \
    - (unsigned char)unsignedCharValue { return (unsigned char)[self unsignedLongLongValue]; } \
    - (short)shortValue { return (short)[self longLongValue]; } \
    - (unsigned short)unsignedShortValue { return (unsigned short)[self unsignedLongLongValue]; } \
    - (int)intValue { return (int)[self longLongValue]; } \
    - (unsigned int)unsignedIntValue { return (unsigned int)[self unsignedLongLongValue]; } \
    - (long)longValue { return (long)[self longLongValue]; } \
    - (unsigned long)unsignedLongValue { return (unsigned long)[self unsignedLongLongValue]; } \
    - (NSInteger)integerValue { return (NSInteger)[self longLongValue]; } \
    - (NSUInteger)unsignedIntegerValue { return (NSUInteger)[self unsignedLongLongValue]; } \
    - (float)floatValue { return (float)[self doubleValue]; }

@interface NSConstantIntegerNumber : NSNumber
@end
@implementation NSConstantIntegerNumber
IMMORTAL_NUMBER
NUMBER_CONVERSIONS
- (const char *)objCType { return ((struct ConstantIntegerNumber *)self)->type; }
- (long long)longLongValue { return (long long)((struct ConstantIntegerNumber *)self)->value; }
- (unsigned long long)unsignedLongLongValue { return ((struct ConstantIntegerNumber *)self)->value; }
- (double)doubleValue {
    switch (*[self objCType]) {
        case 'C': case 'S': case 'I': case 'L': case 'Q':
            return (double)[self unsignedLongLongValue];
        default:return (double)[self longLongValue];
    }
}
- (void)getValue:(void *)buffer {
    NSUInteger size=0;
    NSGetSizeAndAlignment([self objCType],&size,NULL);
    if (size>sizeof(unsigned long long))
        [NSException raise:NSInvalidArgumentException format:@"Invalid constant integer encoding"];
    memcpy(buffer,&((struct ConstantIntegerNumber *)self)->value,size);
}
- (void)getValue:(void *)buffer size:(NSUInteger)size {
    NSUInteger expected=0;
    NSGetSizeAndAlignment([self objCType],&expected,NULL);
    if (size!=expected)
        [NSException raise:NSInvalidArgumentException format:@"Constant number size mismatch"];
    [self getValue:buffer];
}
- (NSString *)descriptionWithLocale:(id)locale {
    NSNumber *value;
    switch (*[self objCType]) {
        case 'C': case 'S': case 'I': case 'L': case 'Q':
            value=[NSNumber numberWithUnsignedLongLong:[self unsignedLongLongValue]];break;
        default:value=[NSNumber numberWithLongLong:[self longLongValue]];break;
    }
    return [value descriptionWithLocale:locale];
}
- (NSString *)description { return [self descriptionWithLocale:nil]; }
@end

@interface NSConstantDoubleNumber : NSNumber
@end
@implementation NSConstantDoubleNumber
IMMORTAL_NUMBER
NUMBER_CONVERSIONS
- (const char *)objCType { return @encode(double); }
- (double)doubleValue { return ((struct ConstantDoubleNumber *)self)->value; }
- (long long)longLongValue { return (long long)[self doubleValue]; }
- (unsigned long long)unsignedLongLongValue { return (unsigned long long)[self doubleValue]; }
- (void)getValue:(void *)buffer { memcpy(buffer,&((struct ConstantDoubleNumber *)self)->value,sizeof(double)); }
- (void)getValue:(void *)buffer size:(NSUInteger)size {
    if (size!=sizeof(double))
        [NSException raise:NSInvalidArgumentException format:@"Constant number size mismatch"];
    [self getValue:buffer];
}
- (NSString *)descriptionWithLocale:(id)locale {
    return [[NSNumber numberWithDouble:[self doubleValue]] descriptionWithLocale:locale];
}
- (NSString *)description { return [self descriptionWithLocale:nil]; }
@end
