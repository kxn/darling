#include <assert.h>
#include <errno.h>
#include <dlfcn.h>
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <mach-o/loader.h>
#include <servers/bootstrap.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>
#include <xpc/xpc.h>
#include "memory-entry-test-utils.h"

typedef void *xpc_pipe_t;
extern xpc_pipe_t xpc_pipe_create_from_port(mach_port_t, uint64_t);
extern int xpc_pipe_routine(xpc_pipe_t, xpc_object_t, xpc_object_t *);
extern int xpc_pipe_routine_reply(xpc_object_t);
extern int xpc_pipe_receive(mach_port_t, xpc_object_t *, uint64_t);
extern void xpc_pipe_invalidate(xpc_pipe_t);
extern xpc_object_t xpc_shmem_create_readonly(const void *, size_t);
extern size_t xpc_shmem_get_length(xpc_object_t);
extern mach_port_t _xpc_shmem_get_mach_port(xpc_object_t);

enum { page = 4096 };
static void *allocate(size_t length) {
    mach_vm_address_t address = 0;
    assert(mach_vm_allocate(mach_task_self(), &address, length, VM_FLAGS_ANYWHERE) == KERN_SUCCESS);
    return (void *)address;
}
static unsigned references(mach_port_t port) {
    mach_port_urefs_t refs = 0;
    assert(mach_port_get_refs(mach_task_self(), port, MACH_PORT_RIGHT_SEND, &refs) == KERN_SUCCESS);
    return refs;
}
static void no_write(void *region) {
    errno = 0;
    assert(mprotect(region, page, PROT_READ | PROT_WRITE) == -1);
    assert(errno == EACCES || errno == EPERM);
}
static void local(void) {
    for (unsigned cycle = 0; cycle < 32; ++cycle) {
        @autoreleasepool {
            unsigned char *source = allocate(2 * page);
            memset(source, 0x42, 2 * page);
            xpc_object_t object = xpc_shmem_create(source, page + 17);
            if (!object || xpc_get_type(object) != XPC_TYPE_SHMEM) {
                Dl_info provider = {0}; dladdr((void *)xpc_shmem_create, &provider);
                fprintf(stderr, "shmem create: object=%p type=%p expected=%p provider=%s source=%p code-offset=%#lx\n",
                    object, object ? xpc_get_type(object) : NULL, XPC_TYPE_SHMEM,
                    provider.dli_fname, source, (uintptr_t)xpc_shmem_create-(uintptr_t)provider.dli_fbase);
            }
            assert(object && xpc_get_type(object) == XPC_TYPE_SHMEM);
            assert(xpc_shmem_get_length(object) == 2 * page);
            mach_port_t port = _xpc_shmem_get_mach_port(object);
            assert(references(port) == 1);
            xpc_object_t copy = xpc_copy(object);
            assert(copy && copy != object && !xpc_equal(copy, object) && xpc_equal(copy, copy));
            assert(references(port) == 2 && xpc_hash(copy) == xpc_hash(object));
            void *mapping = NULL;
            assert(xpc_shmem_map(copy, &mapping) == 2 * page && mapping != source);
            ((unsigned char *)mapping)[page + 9] = 0x79;
            assert(source[page + 9] == 0x79);
            xpc_release(copy); assert(references(port) == 1);
            xpc_object_t readonly = xpc_shmem_create_readonly(source, page);
            assert(readonly);
            void *read_mapping = NULL;
            assert(xpc_shmem_map(readonly, &read_mapping) == page);
            no_write(read_mapping);
            xpc_release(readonly); xpc_release(object);
            source[19] = 0x9b; assert(((unsigned char *)mapping)[19] == 0x9b);
            assert(!munmap(read_mapping, page));
            assert(!munmap(mapping, 2 * page)); assert(!munmap(source, 2 * page));
        }
    }
    xpc_object_t integer = xpc_int64_create(42);
    void *unchanged = (void *)0x1234;
    assert(!xpc_shmem_map(integer, &unchanged) && unchanged == (void *)0x1234);
    assert(!xpc_shmem_get_length(integer) && !_xpc_shmem_get_mach_port(integer));
    xpc_release(integer);
    assert(!xpc_shmem_create(NULL, page));
    void *source = allocate(page);
    assert(!xpc_shmem_create(source, 0));
    assert(!xpc_shmem_create(source, SIZE_MAX));
    assert(!xpc_shmem_create((char *)source + 1, page - 1));
    assert(!munmap(source, page));
    puts("XPC_SHMEM_SOURCE_32_CYCLES_COPY_RIGHTS_PAGE_ROUNDING_ALIAS_READONLY_AND_WRONG_TYPES_OK");
}

// Exercise the real deserializer with kernel-delivered port references.
// The dictionary has one key ("bad") and one shared-memory wire object.
struct malformed_message {
    mach_msg_header_t head;
    mach_msg_body_t body;
    mach_msg_port_descriptor_t port;
    uint32_t wire[9];
};
static void malformed(void) {
    void *source = allocate(page);
    xpc_object_t object = xpc_shmem_create(source, page); assert(object);
    mach_port_t entry = _xpc_shmem_get_mach_port(object), receiver;
    assert(mach_port_allocate(mach_task_self(), MACH_PORT_RIGHT_RECEIVE, &receiver) == KERN_SUCCESS);
    assert(mach_port_insert_right(mach_task_self(), receiver, receiver, MACH_MSG_TYPE_MAKE_SEND) == KERN_SUCCESS);
    uint64_t bad_lengths[] = {0, 1, page - 1, UINT64_MAX, (uint64_t)INT64_MAX + 1};
    for (unsigned repetition = 0; repetition < 16; ++repetition) {
        for (unsigned i = 0; i < sizeof(bad_lengths)/sizeof(*bad_lengths) + 1; ++i) {
            @autoreleasepool {
                struct malformed_message message = {0};
                uint64_t length = i < 5 ? bad_lengths[i] : page;
                message.head.msgh_bits = MACH_MSGH_BITS(MACH_MSG_TYPE_COPY_SEND, 0) | MACH_MSGH_BITS_COMPLEX;
                message.head.msgh_remote_port = receiver;
                message.head.msgh_id = 0x10000000;
                message.head.msgh_size = offsetof(struct malformed_message, wire) + sizeof(message.wire)
                    - (i == 5 ? 4 : 0);
                message.body.msgh_descriptor_count = 1;
                message.port.name = entry;
                message.port.disposition = MACH_MSG_TYPE_COPY_SEND;
                message.port.type = MACH_MSG_PORT_DESCRIPTOR;
                uint32_t wire[] = {0x40585043, 5, 0xf000, 20, 1, 0x00646162,
                    0xc000, (uint32_t)length, (uint32_t)(length >> 32)};
                memcpy(message.wire, wire, sizeof(wire));
                assert(mach_msg(&message.head, MACH_SEND_MSG | MACH_SEND_TIMEOUT,
                    message.head.msgh_size, 0, MACH_PORT_NULL, 5000, MACH_PORT_NULL) == MACH_MSG_SUCCESS);
                xpc_object_t incoming = NULL;
                int result = xpc_pipe_receive(receiver, &incoming, 0);
                if (result != EIO || incoming) fprintf(stderr, "Malformed case=%u length=%llu status=%d incoming=%p\n",
                    i, (unsigned long long)length, result, incoming);
                assert(result == EIO && !incoming);
                assert(references(entry) == 1);
            }
        }
    }
    assert(mach_port_destroy(mach_task_self(), receiver) == KERN_SUCCESS);
    xpc_release(object); assert(!munmap(source, page));
    puts("XPC_SHMEM_SOURCE_96_KERNEL_DELIVERED_MALFORMED_LENGTHS_AND_TRUNCATION_NO_RIGHT_LEAK_OK");
}

struct checkin {
    mach_msg_header_t head;
    mach_msg_body_t body;
    mach_msg_port_descriptor_t receive, send;
};
static void client(const char *service) {
    @autoreleasepool {
        mach_port_t server;
        assert(bootstrap_look_up(bootstrap_port, (char *)service, &server) == KERN_SUCCESS);
        xpc_pipe_t pipe = xpc_pipe_create_from_port(server, 0); assert(pipe);
        assert(mach_port_deallocate(mach_task_self(), server) == KERN_SUCCESS);
        unsigned char *source = allocate(page), *read_source = allocate(page);
        memset(source, 0x32, page); memset(read_source, 0x61, page);
        void *return_mapping = NULL;
        @autoreleasepool {
        xpc_object_t writable = xpc_shmem_create(source, page);
        xpc_object_t readonly = xpc_shmem_create_readonly(read_source, page);
        assert(writable && readonly);
        xpc_object_t request = xpc_dictionary_create(NULL, NULL, 0), reply = NULL;
        xpc_dictionary_set_value(request, "writable", writable);
        xpc_dictionary_set_value(request, "readonly", readonly);
        assert(!xpc_pipe_routine(pipe, request, &reply) && reply);
        assert(source[17] == 0xa5);
        assert(xpc_shmem_map(xpc_dictionary_get_value(reply, "returned"), &return_mapping) == page);
        xpc_release(request); xpc_release(reply); xpc_release(writable); xpc_release(readonly);
        }
        // The inner pool drains temporary serializer/deserializer dictionaries.
        // The map keeps the backing alive after both endpoints release XPC objects.
        ((unsigned char *)return_mapping)[18] = 0xb6;
        assert(source[18] == 0xb6);
        @autoreleasepool {
        xpc_object_t request = xpc_dictionary_create(NULL, NULL, 0), reply = NULL;
        xpc_dictionary_set_bool(request, "finish", true);
        assert(!xpc_pipe_routine(pipe, request, &reply) && reply);
        assert(xpc_dictionary_get_bool(reply, "finished"));
        xpc_release(request); xpc_release(reply);
        }
        assert(!munmap(return_mapping, page));
        assert(!munmap(source, page)); assert(!munmap(read_source, page));
        xpc_pipe_invalidate(pipe); xpc_release((xpc_object_t)pipe);
    }
}
static void interprocess(void) {
    const char *service = "org.linuxcode.xpc-shmem-source";
    mach_port_t receiver;
    assert(mach_port_allocate(mach_task_self(), MACH_PORT_RIGHT_RECEIVE, &receiver) == KERN_SUCCESS);
    assert(mach_port_insert_right(mach_task_self(), receiver, receiver, MACH_MSG_TYPE_MAKE_SEND) == KERN_SUCCESS);
    assert(bootstrap_register(bootstrap_port, (char *)service, receiver) == KERN_SUCCESS);
    pid_t child = fork(); assert(child >= 0);
    if (!child) { client(service); _exit(0); }
    union { struct checkin message; unsigned char bytes[512]; } checkin = {0};
    assert(mach_msg(&checkin.message.head, MACH_RCV_MSG | MACH_RCV_TIMEOUT, 0,
        sizeof(checkin), receiver, 5000, MACH_PORT_NULL) == MACH_MSG_SUCCESS);
    assert(checkin.message.head.msgh_id == 0x77303074 && checkin.message.body.msgh_descriptor_count == 2);
    assert(checkin.message.receive.disposition == MACH_MSG_TYPE_PORT_RECEIVE);
    mach_port_t transport = checkin.message.receive.name;
    assert(mach_port_deallocate(mach_task_self(), checkin.message.send.name) == KERN_SUCCESS);
    void *mapping = NULL;
    @autoreleasepool {
        xpc_object_t request = NULL;
        assert(!xpc_pipe_receive(transport, &request, 0) && request);
        xpc_object_t writable = xpc_dictionary_get_value(request, "writable");
        xpc_object_t readonly = xpc_dictionary_get_value(request, "readonly");
        assert(xpc_get_type(writable) == XPC_TYPE_SHMEM && xpc_get_type(readonly) == XPC_TYPE_SHMEM);
        assert(xpc_shmem_map(writable, &mapping) == page);
        assert(*(unsigned char *)mapping == 0x32);
        void *read_mapping = NULL;
        assert(xpc_shmem_map(readonly, &read_mapping) == page && *(unsigned char *)read_mapping == 0x61);
        no_write(read_mapping); assert(!munmap(read_mapping, page));
        ((unsigned char *)mapping)[17] = 0xa5;
        xpc_object_t reply = xpc_dictionary_create_reply(request); assert(reply);
        xpc_dictionary_set_value(reply, "returned", writable);
        assert(!xpc_pipe_routine_reply(reply));
        xpc_release(reply); xpc_release(request);
    }
    @autoreleasepool {
        xpc_object_t request = NULL;
        assert(!xpc_pipe_receive(transport, &request, 0) && request);
        assert(xpc_dictionary_get_bool(request, "finish") && ((unsigned char *)mapping)[18] == 0xb6);
        xpc_object_t reply = xpc_dictionary_create_reply(request); assert(reply);
        xpc_dictionary_set_bool(reply, "finished", true);
        assert(!xpc_pipe_routine_reply(reply));
        xpc_release(reply); xpc_release(request);
    }
    assert(!munmap(mapping, page));
    int status;
    assert(waitpid(child, &status, 0) == child && WIFEXITED(status) && !WEXITSTATUS(status));
    assert(mach_port_destroy(mach_task_self(), transport) == KERN_SUCCESS);
    assert(mach_port_destroy(mach_task_self(), receiver) == KERN_SUCCESS);
    puts("XPC_SHMEM_SOURCE_REAL_XPC_DICTIONARY_OOL_PORTS_ROUNDTRIP_BIDIRECTIONAL_READONLY_AND_LIFETIME_OK");
}
int main(int argc, const char **argv) {
    setbuf(stdout, NULL);
    assert(argc == 2 && strlen(argv[1]) == 32);
    unsigned char expected[16];
    for (unsigned i = 0; i < 16; ++i) {
        unsigned byte;
        assert(sscanf(argv[1] + 2 * i, "%2x", &byte) == 1);
        expected[i] = byte;
    }
    Dl_info provider = {0}; assert(dladdr((void *)xpc_shmem_create, &provider));
    const struct mach_header_64 *header = provider.dli_fbase;
    assert(header->magic == MH_MAGIC_64);
    const struct load_command *command = (const void *)(header + 1);
    bool matched = false;
    for (unsigned i = 0; i < header->ncmds; ++i) {
        if (command->cmd == LC_UUID) {
            const struct uuid_command *uuid = (const void *)command;
            matched = !memcmp(uuid->uuid, expected, 16);
        }
        command = (const void *)((const char *)command + command->cmdsize);
    }
    if (!matched) { fputs("XPC_SHMEM_SOURCE_LOADED_LIBRARY_UUID_MISMATCH\n", stderr); return 3; }
    puts("XPC_SHMEM_SOURCE_LOADED_LIBRARY_UUID_VERIFIED");
    unsigned long server = server_pid();
    unsigned baseline = backing_files(server);
    local(); wait_for_backing_count(server, baseline);
    malformed(); wait_for_backing_count(server, baseline);
    interprocess(); wait_for_backing_count(server, baseline);
    puts("XPC_SHMEM_SOURCE_BACKING_FDS_RETURN_TO_BASELINE_AFTER_RECONCILIATION_OK");
    return 0;
}
