// Immutable literal layouts follow clang/lib/CodeGen/CGObjCMac.cpp.
#import <Foundation/Foundation.h>

struct ConstantArray { Class isa; NSUInteger count; id const *objects; };
struct ConstantDictionary { Class isa; NSUInteger options; NSUInteger count; id const *keys; id const *objects; };
extern struct ConstantArray __NSArray0__struct;
extern struct ConstantDictionary __NSDictionary0__struct;

#define IMMORTAL_OBJECT \
    - (id)retain { return self; } \
    - (oneway void)release {} \
    - (id)autorelease { return self; } \
    - (NSUInteger)retainCount { return NSUIntegerMax; } \
    - (id)copyWithZone:(NSZone *)zone { return self; }

@interface NSConstantArray : NSArray
@end
@implementation NSConstantArray
IMMORTAL_OBJECT
+ (void)load { __NSArray0__struct.isa = self; }
- (NSUInteger)count { return ((struct ConstantArray *)self)->count; }
- (id)objectAtIndex:(NSUInteger)index {
    struct ConstantArray *layout = (void *)self;
    if (index >= layout->count) {
        [NSException raise:NSRangeException format:@"Constant array index %lu exceeds count %lu", (unsigned long)index, (unsigned long)layout->count];
    }
    return layout->objects[index];
}
- (NSUInteger)countByEnumeratingWithState:(NSFastEnumerationState *)state objects:(id __unsafe_unretained [])buffer count:(NSUInteger)length {
    if (state->state) return 0;
    state->state = 1;
    state->itemsPtr = (id __unsafe_unretained *)((struct ConstantArray *)self)->objects;
    state->mutationsPtr = (unsigned long *)&((struct ConstantArray *)self)->count;
    return ((struct ConstantArray *)self)->count;
}
@end

@interface NSConstantDictionary : NSDictionary
@end
@implementation NSConstantDictionary
IMMORTAL_OBJECT
+ (void)load { __NSDictionary0__struct.isa = self; }
- (NSUInteger)count { return ((struct ConstantDictionary *)self)->count; }
- (id)objectForKey:(id)key {
    struct ConstantDictionary *layout = (void *)self;
    if (!key) return nil;
    for (NSUInteger index = 0; index < layout->count; ++index) {
        if (key == layout->keys[index] || [key isEqual:layout->keys[index]]) return layout->objects[index];
    }
    return nil;
}
- (NSEnumerator *)keyEnumerator {
    struct ConstantDictionary *layout = (void *)self;
    return [[NSArray arrayWithObjects:layout->keys count:layout->count] objectEnumerator];
}
- (NSUInteger)countByEnumeratingWithState:(NSFastEnumerationState *)state objects:(id __unsafe_unretained [])buffer count:(NSUInteger)length {
    if (state->state) return 0;
    state->state = 1;
    state->itemsPtr = (id __unsafe_unretained *)((struct ConstantDictionary *)self)->keys;
    state->mutationsPtr = (unsigned long *)&((struct ConstantDictionary *)self)->count;
    return ((struct ConstantDictionary *)self)->count;
}
@end
