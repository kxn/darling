// Contracts follow the pinned original x86_64 libxpc routines. Storage follows
// Darling's existing OS_xpc_object C header, not Apple's private object layout.
#import <Foundation/Foundation.h>
#include <xpc/xpc.h>
#include <mach/mach.h>
#include <objc/runtime.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <errno.h>

@interface OS_xpc_object : NSObject
+ (NSUInteger)instanceSize;
@end
@interface OS_xpc_mach_send_once : OS_xpc_object
- (instancetype)initWithOwnedRight:(mach_port_t)right;
- (mach_port_t)extractRight;
- (char *)xpcDescription;
@end

struct OnceObject {
    void *isa;
    int32_t internalReferences, externalReferences;
    _Atomic(mach_port_t) right;
};
_Static_assert(offsetof(struct OnceObject, right)==16, "Pinned Darling object header");
_Static_assert(sizeof(struct OnceObject)==24, "Pinned adapter instance size");
static const mach_port_t consumed = 0xfffffffeU;

// Darwin XPC type identifiers are aliases of the actual Objective-C Class.
__asm__(".globl __xpc_type_mach_send_once\n.equiv __xpc_type_mach_send_once, _OBJC_CLASS_$_OS_xpc_mach_send_once");
extern const struct _xpc_type_s _xpc_type_mach_send_once;

@implementation OS_xpc_mach_send_once
+ (void)load {
    [OS_xpc_object class];
    if ([OS_xpc_object instanceSize]!=16) {
        fprintf(stderr,"Darling XPC object ABI changed\n");__builtin_trap();
    }
}
+ (NSUInteger)instanceSize { return sizeof(struct OnceObject); }
- (instancetype)initWithOwnedRight:(mach_port_t)right {
    self=[super init];
    if (self) atomic_init(&((struct OnceObject *)self)->right,right);
    return self;
}
- (mach_port_t)extractRight {
    mach_port_t result=atomic_exchange(&((struct OnceObject *)self)->right,consumed);
    if (result==consumed) {
        fprintf(stderr,"XPC send-once right extracted more than once\n");__builtin_trap();
    }
    return result;
}
- (void)dealloc {
    mach_port_t right=atomic_exchange(&((struct OnceObject *)self)->right,MACH_PORT_DEAD);
    if (right!=MACH_PORT_NULL && right!=MACH_PORT_DEAD && right!=consumed) {
        if (mach_port_deallocate(mach_task_self(),right)!=KERN_SUCCESS) {
            fprintf(stderr,"XPC send-once right disposal failed\n");__builtin_trap();
        }
    }
    [super dealloc];
}
- (NSUInteger)hash { return atomic_load(&((struct OnceObject *)self)->right); }
- (BOOL)isEqual:(id)other {
    return object_getClass(other)==[OS_xpc_mach_send_once class] &&
        atomic_load(&((struct OnceObject *)self)->right)==atomic_load(&((struct OnceObject *)other)->right);
}
- (char *)xpcDescription {
    char *description=NULL;
    asprintf(&description,"<OS_xpc_mach_send_once: right = %u>",atomic_load(&((struct OnceObject *)self)->right));
    return description;
}
// The inherited -copy retains this same immutable capability container, just
// like the pinned native copy routine. A send-once right is never duplicated.
- (BOOL)serializable { return NO; }
- (NSUInteger)serializationLength { return 0; }
- (BOOL)serialize:(id)serializer { errno=ENOTSUP;return NO; }
@end

xpc_object_t xpc_mach_send_once_create(mach_port_t right) {
    return (xpc_object_t)[[OS_xpc_mach_send_once alloc] initWithOwnedRight:right];
}
mach_port_t xpc_mach_send_once_extract_right(xpc_object_t object) {
    if (xpc_get_type(object)!=&_xpc_type_mach_send_once) return MACH_PORT_NULL;
    return [(OS_xpc_mach_send_once *)object extractRight];
}
