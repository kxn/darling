#import <objc/NSObject.h>
#import <objc/runtime.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stddef.h>
#include <errno.h>

/* darling-libdispatch 380f03c event/event_internal.h, KEVENT + HAVE_MACH.
 * This source kind has no Linux backend. Its real create callback rejects it;
 * no dispatch object or fictitious notification listener is created. */
struct LinuxcodeSourceType {
    const char *kind;
    int8_t filter;
    uint8_t action;
    uint8_t per_trigger_qos:1, strict:1, allow_empty_mask:1;
    uint8_t timer_flags;
    uint16_t flags,data;
    uint32_t fflags,mask,size;
    void *(*create)(const void *,uintptr_t,uintptr_t);
    void *update_mux,*merge_event,*merge_message;
};
_Static_assert(offsetof(struct LinuxcodeSourceType,create)==32,"dispatch source create ABI");
_Static_assert(sizeof(struct LinuxcodeSourceType)==64,"dispatch source descriptor ABI");
static void *unsupported_exclaves_source(const void *type,uintptr_t handle,uintptr_t mask) {
    (void)type;(void)handle;(void)mask;
    errno=ENOTSUP;
    return NULL;
}
const struct LinuxcodeSourceType _dispatch_source_type_exclaves_notification={
    .kind="exclaves_notification_unsupported",.create=unsupported_exclaves_source
};

/* The pinned 25G83 libdispatch defines this fieldless abstract marker between
 * OS_dispatch_queue and OS_dispatch_queue_serial. Queue storage and scheduling
 * remain in Darling's real libdispatch implementation. */
@protocol OS_dispatch_queue <NSObject> @end
@protocol OS_dispatch_queue_serial_executor <OS_dispatch_queue> @end
@interface OS_dispatch_queue : NSObject @end
@interface OS_dispatch_queue_serial_executor : OS_dispatch_queue <OS_dispatch_queue_serial_executor>
@property(readonly) NSUInteger hash;
@property(readonly) Class superclass;
@property(readonly,copy) NSString *description;
@property(readonly,copy) NSString *debugDescription;
- (instancetype)init __attribute__((unavailable("Use dispatch queue constructors")));
@end

@implementation OS_dispatch_queue_serial_executor
@dynamic hash,superclass,description,debugDescription;
+ (void)load {
    Class parent=objc_getClass("OS_dispatch_queue");
    Class serial=objc_getClass("OS_dispatch_queue_serial");
    /* objc4's class_setSuperclass requires realized classes; its size query
     * does not realize them. An ordinary class message performs that work. */
    if (parent) (void)[(id)parent class];
    if (serial) (void)[(id)serial class];
    (void)[(id)self class];
    if (!parent || !serial || class_getSuperclass(self)!=parent ||
        class_getInstanceSize(parent)!=sizeof(void *) ||
        class_getInstanceSize(self)!=sizeof(void *) ||
        class_getInstanceSize(serial)!=sizeof(void *)) {
        fputs("dispatch executor compatibility: unexpected queue class layout\n",stderr);
        abort();
    }
    Class previous=class_getSuperclass(serial);
    if (previous==self) return;
    if (previous!=parent) {
        fputs("dispatch executor compatibility: unexpected serial queue ancestry\n",stderr);
        abort();
    }
    /* objc4 takes its runtime lock, updates both class/metaclass subclass lists
     * and flushes caches. The inserted class adds no storage or RR overrides. */
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
    if (class_setSuperclass(serial,self)!=parent) abort();
#pragma clang diagnostic pop
}
- (instancetype)init {
    fputs("dispatch executor: Objective-C init is unavailable; use dispatch queue constructors\n",stderr);
    __builtin_trap();
}
@end
