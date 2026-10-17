#include <TargetConditionals.h>
#include <objc/objc-internal.h>
#include <objc/Protocol.h>
#include <assert.h>
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

@interface LCTagBase : NSObject
- (uintptr_t)marker;
@end
@implementation LCTagBase
- (uintptr_t)marker { return 0x14327698; }
@end
@interface LCTagBasic : LCTagBase @end
@implementation LCTagBasic @end
@interface LCTagExtended : LCTagBase @end
@implementation LCTagExtended @end
@interface LCTagLast : LCTagBase @end
@implementation LCTagLast @end

extern void objc_storeStrong(id *, id);
extern id objc_initWeak(id *, id);
extern id objc_loadWeakRetained(id *);
extern void objc_destroyWeak(id *);

static unsigned tests;
static void check(objc_tag_index_t tag, Class cls, uintptr_t value) {
    id ptr = _objc_makeTaggedPointer(tag, value);
    assert(_objc_isTaggedPointer(ptr));
    assert(_objc_getTaggedPointerTag(ptr) == tag);
    assert(_objc_getTaggedPointerValue(ptr) == value);
    assert(object_getClass(ptr) == cls);
    assert(objc_opt_class(ptr) == cls);
    assert(objc_opt_isKindOfClass(ptr, cls));
    assert(objc_opt_isKindOfClass(ptr, [LCTagBase class]));
    assert(!objc_opt_isKindOfClass(ptr, [Protocol class]));
    assert(objc_opt_respondsToSelector(ptr, @selector(marker)));
    assert(!objc_opt_respondsToSelector(ptr, sel_registerName("noSuchDarlingSelector")));
    assert([(LCTagBase *)ptr marker] == 0x14327698);
    assert(objc_retain(ptr) == ptr);
    objc_release(ptr);
    id strong = nil;
    objc_storeStrong(&strong, ptr);
    assert(strong == ptr);
    objc_storeStrong(&strong, nil);
    id weak = nil;
    assert(objc_initWeak(&weak, ptr) == ptr);
    id retained = objc_loadWeakRetained(&weak);
    assert(retained == ptr);
    objc_release(retained);
    objc_destroyWeak(&weak);
    tests++;
}

int main(void) {
    setbuf(stdout, NULL);
    puts("SOURCE_OBJC_TAGGED_MAIN_ENTERED");
    Dl_info owner;
    assert(dladdr((void *)object_getClass, &owner));
    printf("OBJC_RUNTIME_OWNER %s\n", owner.dli_fname);
    assert(_objc_taggedPointersEnabled());
    _objc_registerTaggedPointerClass(OBJC_TAG_1, [LCTagBasic class]);
    _objc_registerTaggedPointerClass((objc_tag_index_t)200, [LCTagExtended class]);
    _objc_registerTaggedPointerClass(OBJC_TAG_Last52BitPayload, [LCTagLast class]);
    uintptr_t values[] = {0, 1, 255, 4096, (UINT64_C(1) << 51) - 1, (UINT64_C(1) << 52) - 1};
    for (unsigned i = 0; i < sizeof(values) / sizeof(values[0]); i++) {
        check(OBJC_TAG_1, [LCTagBasic class], values[i]);
        check((objc_tag_index_t)200, [LCTagExtended class], values[i]);
        check(OBJC_TAG_Last52BitPayload, [LCTagLast class], values[i]);
    }
    check(OBJC_TAG_1, [LCTagBasic class], (UINT64_C(1) << 60) - 1);
    id object = [LCTagBase new];
    assert(!_objc_isTaggedPointer(object));
    assert(object_getClass(object) == [LCTagBase class]);
    assert([object marker] == 0x14327698);
    [object release];
    assert(object_getClass(nil) == Nil && objc_opt_class(nil) == Nil);
    printf("SOURCE_OBJC_TAGGED_%u_BASIC_EXTENDED_BOUNDARIES_CLASS_DISPATCH_RR_WEAK_AND_HEAP_OK\n", tests);
    return 0;
}
