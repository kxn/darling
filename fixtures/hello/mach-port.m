#import <Foundation/Foundation.h>
#import <objc/runtime.h>
#include <mach/mach.h>
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <dlfcn.h>
#include <string.h>

@interface Recorder : NSObject <NSMachPortDelegate> { @public unsigned count, dataCount; mach_msg_id_t identifier; }
@end
@implementation Recorder
- (void)handleMachMessage:(void *)message {
    mach_msg_header_t *header = message; ++count; identifier = header->msgh_id;
    if (identifier == 732) {
        struct { mach_msg_header_t header; mach_msg_body_t body; } *body = message;
        assert(header->msgh_bits & MACH_MSGH_BITS_COMPLEX);
        assert(body->body.msgh_descriptor_count == 1);
        assert(header->msgh_size >= sizeof(*body) + sizeof(mach_msg_ool_descriptor_t));
        mach_msg_ool_descriptor_t *descriptor = (void *)(body + 1);
        assert(descriptor->type == MACH_MSG_OOL_DESCRIPTOR && descriptor->size == 1);
        assert(*(const char *)descriptor->address == 'x'); ++dataCount;
    }
    mach_msg_destroy(header);
}
@end

int main(void) {
    @autoreleasepool {
        Class portClass = NSClassFromString(@"NSMachPort"); assert(portClass);
        Method method = class_getInstanceMethod(portClass, @selector(machPort)); Dl_info owner;
        assert(method && dladdr((void *)method_getImplementation(method), &owner));
        assert(strstr(owner.dli_fname, "libFND.dylib"));
        NSMachPort *port = [portClass new]; assert(port && port.valid);
        mach_port_t number = port.machPort; mach_port_type_t type = 0;
        assert(mach_port_type(mach_task_self(), number, &type) == KERN_SUCCESS);
        assert((type & (MACH_PORT_TYPE_SEND | MACH_PORT_TYPE_RECEIVE)) == (MACH_PORT_TYPE_SEND | MACH_PORT_TYPE_RECEIVE));
        NSMachPort *borrowed = [[portClass alloc] initWithMachPort:number options:NSMachPortDeallocateNone];
        assert(borrowed && borrowed.valid && borrowed.machPort == number);
        // CFMachPort may return the same cached object for an existing name.
        // Releasing another reference must preserve the live receive port.
        [borrowed release]; assert(port.valid);
        Recorder *recorder = [Recorder new]; port.delegate = recorder;
        NSRunLoop *loop = [NSRunLoop currentRunLoop];
        [port scheduleInRunLoop:loop forMode:NSDefaultRunLoopMode];
        assert([port sendBeforeDate:[NSDate dateWithTimeIntervalSinceNow:1] msgid:731 components:nil from:nil reserved:0]);
        NSDate *limit = [NSDate dateWithTimeIntervalSinceNow:2];
        while (!recorder->count && [limit timeIntervalSinceNow] > 0)
            [loop runMode:NSDefaultRunLoopMode beforeDate:limit];
        assert(recorder->count == 1 && recorder->identifier == 731);
        NSMutableArray *data = [NSMutableArray arrayWithObject:[NSData dataWithBytes:"x" length:1]];
        assert([port sendBeforeDate:[NSDate dateWithTimeIntervalSinceNow:1] msgid:732 components:data from:nil reserved:0]);
        limit = [NSDate dateWithTimeIntervalSinceNow:2];
        while (recorder->count < 2 && [limit timeIntervalSinceNow] > 0)
            [loop runMode:NSDefaultRunLoopMode beforeDate:limit];
        assert(recorder->count == 2 && recorder->dataCount == 1 && recorder->identifier == 732);
        [port removeFromRunLoop:loop forMode:NSDefaultRunLoopMode];
        port.delegate = nil; [port invalidate]; [port invalidate]; assert(!port.valid);
        type = 0;
        kern_return_t status = mach_port_type(mach_task_self(), number, &type);
        fprintf(stderr, "MACH_PORT_POST_INVALIDATION_TYPE status=%d type=%u\n", status, type);
        // Right disposition after invalidation is observed, not asserted as
        // complete ownership compatibility. Clean up this test's own name.
        if (status == KERN_SUCCESS) mach_port_destroy(mach_task_self(), number);
        [recorder release]; [port release];
        puts("BASELINE_MACH_PORT_REAL_RIGHTS_RUNLOOP_RAW_AND_OOL_DATA_MESSAGES_INVALIDATION_OK");
    }
}
