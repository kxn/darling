// Pinned Intel Foundation 25G83: NSConstantFloatNumber has instanceStart 8,
// instanceSize 12, and one float ivar _value at offset 8 (alignment 2^2).
// The literal storage is emitted by Apple clang; this supplies NSNumber methods.
#import <Foundation/Foundation.h>
#include <string.h>

@interface NSConstantFloatNumber : NSNumber { float _value; }
@end
@implementation NSConstantFloatNumber
- (id)retain { return self; }
- (oneway void)release {}
- (id)autorelease { return self; }
- (NSUInteger)retainCount { return NSUIntegerMax; }
- (id)copyWithZone:(NSZone *)zone { return self; }
- (const char *)objCType { return @encode(float); }
- (float)floatValue { return _value; }
- (double)doubleValue { return _value; }
- (BOOL)boolValue { return _value != 0; }
- (char)charValue { return (char)_value; }
- (unsigned char)unsignedCharValue { return (unsigned char)_value; }
- (short)shortValue { return (short)_value; }
- (unsigned short)unsignedShortValue { return (unsigned short)_value; }
- (int)intValue { return (int)_value; }
- (unsigned int)unsignedIntValue { return (unsigned int)_value; }
- (long)longValue { return (long)_value; }
- (unsigned long)unsignedLongValue { return (unsigned long)_value; }
- (long long)longLongValue { return (long long)_value; }
- (unsigned long long)unsignedLongLongValue { return (unsigned long long)_value; }
- (NSInteger)integerValue { return (NSInteger)_value; }
- (NSUInteger)unsignedIntegerValue { return (NSUInteger)_value; }
- (void)getValue:(void *)buffer { memcpy(buffer, &_value, sizeof(float)); }
- (void)getValue:(void *)buffer size:(NSUInteger)size {
    if (size != sizeof(float))
        [NSException raise:NSInvalidArgumentException format:@"Constant float size mismatch"];
    [self getValue:buffer];
}
- (NSString *)descriptionWithLocale:(id)locale {
    return [[NSNumber numberWithFloat:_value] descriptionWithLocale:locale];
}
- (NSString *)description { return [self descriptionWithLocale:nil]; }
@end
