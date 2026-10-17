#import <Foundation/Foundation.h>
#include <assert.h>
#include <dlfcn.h>
#include <mach/mach.h>
#include <pthread.h>
#include <servers/bootstrap.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>
#include <uuid/uuid.h>
#include <xpc/xpc.h>

extern int xpc_pipe_receive(mach_port_t, xpc_object_t*, uint64_t);
extern int xpc_pipe_routine_reply(xpc_object_t);
typedef int64_t (*Query)(NSString*, bool*);
static Query query;
static const char* service = "com.apple.mobileassetd.v2";
static const int64_t wideError = -INT64_C(0x123456789);
static void check(NSString* asset, int64_t code, bool expected, bool nullOutput) {
    struct { unsigned char before; bool value; unsigned char after; } out = {0x35, true, 0x79};
    assert(query(asset, nullOutput ? NULL : &out.value) == code);
    assert(out.before == 0x35 && out.after == 0x79);
    assert(nullOutput || out.value == expected);
}
static void* worker(void* context) {
    unsigned worker = (unsigned)(uintptr_t)context;
    @autoreleasepool {
        for (unsigned j = 0; j < 8; ++j) {
            NSString* asset = [NSString stringWithFormat:@"org.linuxcode.thread.%u.%u", worker, j];
            check(asset, 0, (worker + j) % 2, false);
        }
    }
    return NULL;
}
static void client(void) {
    @autoreleasepool {
        for (unsigned j = 0; j < 10; ++j) {
            id asset = j == 6 ? nil : j == 7 ? (id)@42 :
                [NSString stringWithFormat:@"org.linuxcode.case.%u", j];
            int64_t code = j == 2 ? 13 : j == 3 ? wideError : 0;
            bool expected = j == 0 || j == 4 || j == 5 || j == 7 || j == 9;
            check(asset, code, expected, j == 5);
        }
        pthread_t threads[8];
        for (unsigned j = 0; j < 8; ++j) assert(!pthread_create(&threads[j], NULL, worker, (void*)(uintptr_t)j));
        for (unsigned j = 0; j < 8; ++j) assert(!pthread_join(threads[j], NULL));
    }
}
struct checkin {
    mach_msg_header_t header;
    mach_msg_body_t body;
    mach_msg_port_descriptor_t receive, send;
};
int main(int argc, char** argv) {
    assert(argc == 2); setbuf(stdout, NULL);
    void* h = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!h) fprintf(stderr, "%s\n", dlerror());
    assert(h);
    query = (Query)dlsym(h, "MAGetPallasEnabled");
    Query internal = (Query)dlsym(h, "_MAsendGetPallasEnabled");
    Dl_info owner, internalOwner;
    assert(query && internal && dladdr((void*)query, &owner) && dladdr((void*)internal, &internalOwner));
    assert(owner.dli_fbase == internalOwner.dli_fbase && !strcmp(owner.dli_fname, argv[1]));
    puts("MOBILEASSET_PALLAS_API_OWNED_BY_ACTUAL_SOURCE_FRAMEWORK_OK");
    mach_port_t existing;
    assert(bootstrap_look_up(bootstrap_port, (char*)service, &existing) == BOOTSTRAP_UNKNOWN_SERVICE);
    @autoreleasepool {
        check(@"org.linuxcode.absent", 1, false, false);
        check(nil, 1, false, true);
        bool enabled = true; assert(internal(nil, &enabled) == 1 && !enabled);
    }
    puts("MOBILEASSET_PALLAS_REAL_ABSENT_SERVICE_FAILURE_AND_BOOLEAN_OUTPUT_ABI_OK");
    mach_port_t receiver;
    assert(!mach_port_allocate(mach_task_self(), MACH_PORT_RIGHT_RECEIVE, &receiver));
    assert(!mach_port_insert_right(mach_task_self(), receiver, receiver, MACH_MSG_TYPE_MAKE_SEND));
    assert(!bootstrap_register(bootstrap_port, (char*)service, receiver));
    pid_t child = fork(); assert(child >= 0);
    if (!child) { client(); _exit(0); }
    bool seen[8][8] = {{false}};
    for (unsigned j = 0; j < 74; ++j) {
        @autoreleasepool {
            union { struct checkin checkin; unsigned char bytes[512]; } message = {0};
            assert(!mach_msg(&message.checkin.header, MACH_RCV_MSG | MACH_RCV_TIMEOUT, 0,
                sizeof(message), receiver, 10000, MACH_PORT_NULL));
            assert(message.checkin.header.msgh_id == 0x77303074 && message.checkin.body.msgh_descriptor_count == 2);
            assert(message.checkin.receive.disposition == MACH_MSG_TYPE_PORT_RECEIVE);
            mach_port_t transport = message.checkin.receive.name;
            xpc_object_t request = NULL;
            assert(!xpc_pipe_receive(transport, &request, 0) && request);
            assert(xpc_get_type(xpc_dictionary_get_value(request, "messageAction")) == XPC_TYPE_INT64);
            assert(xpc_dictionary_get_int64(request, "messageAction") == 32);
            assert(!strcmp(xpc_dictionary_get_string(request, "requestType"), "requestTypeSync"));
            assert(!strcmp(xpc_dictionary_get_string(request, "clientName"), getprogname()));
            const char* identifier = xpc_dictionary_get_string(request, "connectionIdentifier");
            uuid_t uuid; assert(identifier && strlen(identifier) == 36 && !uuid_parse(identifier, uuid));
            const char* asset = xpc_dictionary_get_string(request, "AssetType");
            int64_t result = 0; bool enabled = false;
            if (j < 10) {
                if (j == 6 || j == 7) assert(!xpc_dictionary_get_value(request, "AssetType"));
                else {
                    char expected[64]; snprintf(expected, sizeof(expected), "org.linuxcode.case.%u", j);
                    assert(asset && !strcmp(asset, expected));
                }
                result = j == 2 ? 13 : j == 3 ? wideError : 0;
                enabled = j == 0 || j == 2 || j == 3 || j == 4 || j == 5 || j == 7 || j == 9;
            } else {
                unsigned thread, iteration; char tail;
                assert(asset && sscanf(asset, "org.linuxcode.thread.%u.%u%c", &thread, &iteration, &tail) == 2);
                assert(thread < 8 && iteration < 8 && !seen[thread][iteration]); seen[thread][iteration] = true;
                enabled = (thread + iteration) % 2;
            }
            xpc_object_t reply = xpc_dictionary_create_reply(request); assert(reply);
            if (j != 4) {
                if (j == 9) xpc_dictionary_set_string(reply, "Result", "wrong-type");
                else xpc_dictionary_set_int64(reply, "Result", result);
            }
            if (j == 8) xpc_dictionary_set_string(reply, "pallasEnabled", "wrong-type");
            else xpc_dictionary_set_bool(reply, "pallasEnabled", enabled);
            assert(!xpc_pipe_routine_reply(reply));
            xpc_release(reply); xpc_release(request);
            assert(!mach_port_destroy(mach_task_self(), transport));
            assert(!mach_port_deallocate(mach_task_self(), message.checkin.send.name));
        }
    }
    int status; assert(waitpid(child, &status, 0) == child && WIFEXITED(status) && !WEXITSTATUS(status));
    assert(!mach_port_destroy(mach_task_self(), receiver));
    puts("MOBILEASSET_PALLAS_REAL_FORKED_XPC_NATIVE_ENVELOPE_TRUE_FALSE_WIDE_ERRORS_NULL_NONSTRING_AND_TYPED_REPLIES_OK");
    puts("MOBILEASSET_PALLAS_REAL_EIGHT_THREADS_64_INDEPENDENT_XPC_REQUEST_REPLY_CYCLES_OK");
    return 0;
}
