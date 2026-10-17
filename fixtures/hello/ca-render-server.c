#include <assert.h>
#include <CoreFoundation/CoreFoundation.h>
#include <mach/mach.h>
#include <mach/mig_errors.h>
#include <mach/ndr.h>
#include <servers/bootstrap.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern bool CARenderServerGetDebugOption(mach_port_t, unsigned int);
extern bool darling_ca_native_query(mach_port_t, unsigned int);
extern void CARenderServerSetDebugOption(mach_port_t, unsigned int, bool);
extern void darling_ca_native_set_option(mach_port_t, unsigned int, bool);
extern uint32_t CARenderServerGetFrameCounter(mach_port_t);
extern uint32_t darling_ca_native_frame_counter(mach_port_t);
static kern_return_t native_status;
static unsigned lookup_calls;
mach_port_t darling_ca_oracle_lookup(const char *unused) {
    assert(unused == NULL);
    ++lookup_calls;
    mach_port_t port = MACH_PORT_NULL;
    if (bootstrap_look_up(bootstrap_port, "com.apple.CARenderServer", &port))
        return MACH_PORT_NULL;
    return port;
}
void darling_ca_oracle_result(kern_return_t result) { native_status = result; }

struct request { mach_msg_header_t head; NDR_record_t ndr; uint32_t option; };
struct reply { mach_msg_header_t head; NDR_record_t ndr; kern_return_t result; uint32_t enabled; };
struct server {
    mach_port_t port, extra;
    unsigned mode, option, kind;
    bool enabled;
    unsigned char *data;
    size_t length;
};
static unsigned exchanges;

static void *serve(void *opaque) {
    struct server *server = opaque;
    union { struct request request; unsigned char bytes[512]; } input = {0};
    kern_return_t status = mach_msg(&input.request.head, MACH_RCV_MSG | MACH_RCV_TIMEOUT,
            0, sizeof(input), server->port, 5000, MACH_PORT_NULL);
    assert(status == MACH_MSG_SUCCESS);
    assert(input.request.head.msgh_id == (server->kind == 1 ? 40257 : server->kind == 2 ? 40231 : 40256));
    assert(input.request.head.msgh_size == (server->kind == 1 ? 40 : sizeof(struct request)));
    assert(input.request.head.msgh_local_port == server->port);
    assert(MACH_MSGH_BITS_REMOTE(input.request.head.msgh_bits) == MACH_MSG_TYPE_PORT_SEND_ONCE);
    assert(!memcmp(&input.request.ndr, &NDR_record, sizeof(NDR_record)));
    assert(input.request.option == server->option);
    if (server->kind == 1) {
        uint32_t enabled;
        memcpy(&enabled, input.bytes + sizeof(struct request), sizeof(enabled));
        assert(enabled == server->enabled);
    }
    ++exchanges;
    if (server->mode == 9 || (server->kind == 2 && server->mode == 104)) {
        // Destroying the request's send-once right delivers an actual death
        // notification, rather than manufacturing the notification payload.
        mach_msg_destroy(&input.request.head);
        return NULL;
    }
    if (server->kind == 2 && server->mode != 101) {
        struct {
            mach_msg_header_t head;
            mach_msg_body_t body;
            mach_msg_ool_descriptor_t data;
            NDR_record_t ndr;
            uint32_t count;
        } output = {0};
        _Static_assert(sizeof(output) == 56, "stats wire reply");
        output.head.msgh_bits = MACH_MSGH_BITS(MACH_MSG_TYPE_MOVE_SEND_ONCE, 0) | MACH_MSGH_BITS_COMPLEX;
        output.head.msgh_id = server->mode == 100 ? 40332 : 40331;
        output.head.msgh_remote_port = input.request.head.msgh_remote_port;
        output.head.msgh_size = server->mode == 103 ? 52 : sizeof(output);
        output.body.msgh_descriptor_count = 1;
        vm_address_t data = 0;
        assert(vm_allocate(mach_task_self(), &data, server->length, VM_FLAGS_ANYWHERE) == KERN_SUCCESS);
        memcpy((void *)data, server->data, server->length);
        output.data.address = (void *)data;
        output.data.size = (mach_msg_size_t)server->length;
        output.data.type = MACH_MSG_OOL_DESCRIPTOR;
        output.data.copy = MACH_MSG_VIRTUAL_COPY;
        output.data.deallocate = TRUE;
        output.ndr = NDR_record;
        output.count = (uint32_t)server->length + (server->mode == 102 ? 1 : 0);
        assert(mach_msg(&output.head, MACH_SEND_MSG | MACH_SEND_TIMEOUT,
                    output.head.msgh_size, 0, MACH_PORT_NULL, 5000, MACH_PORT_NULL) == MACH_MSG_SUCCESS);
        return NULL;
    }
    struct reply output = {0};
    output.head.msgh_bits = MACH_MSGH_BITS(MACH_MSG_TYPE_MOVE_SEND_ONCE, 0);
    output.head.msgh_remote_port = input.request.head.msgh_remote_port;
    output.head.msgh_id = server->kind == 1 ? 40357 : server->kind == 2 ? 40331 : 40356;
    output.head.msgh_size = server->kind ? 36 : sizeof(output);
    output.ndr = NDR_record;
    output.enabled = server->mode == 0 ? 0 : server->mode == 2 ? UINT32_MAX : 1;
    switch (server->mode) {
    case 101: output.result = KERN_FAILURE; break;
    case 3: output.head.msgh_size = 36; output.result = KERN_FAILURE; break;
    case 4: output.head.msgh_size = 36; break;
    case 5: output.head.msgh_id++; break;
    case 6: output.head.msgh_bits |= MACH_MSGH_BITS_COMPLEX; break;
    case 7:
        output.head.msgh_bits = MACH_MSGH_BITS(MACH_MSG_TYPE_MOVE_SEND_ONCE, MACH_MSG_TYPE_MAKE_SEND);
        output.head.msgh_local_port = server->extra;
        break;
    case 8: output.result = KERN_FAILURE; break;
    }
    status = mach_msg(&output.head, MACH_SEND_MSG | MACH_SEND_TIMEOUT,
            output.head.msgh_size, 0, MACH_PORT_NULL, 5000, MACH_PORT_NULL);
    assert(status == MACH_MSG_SUCCESS);
    return NULL;
}

static mach_port_t make_port(void) {
    mach_port_t port;
    assert(mach_port_allocate(mach_task_self(), MACH_PORT_RIGHT_RECEIVE, &port) == KERN_SUCCESS);
    assert(mach_port_insert_right(mach_task_self(), port, port, MACH_MSG_TYPE_MAKE_SEND) == KERN_SUCCESS);
    return port;
}
static unsigned refs(mach_port_t port) {
    mach_port_urefs_t count = 0;
    assert(mach_port_get_refs(mach_task_self(), port, MACH_PORT_RIGHT_SEND, &count) == KERN_SUCCESS);
    return count;
}
static void exercise(mach_port_t port, mach_port_t extra, unsigned mode, bool native, bool discovery) {
    struct server server = {.port=port, .extra=extra, .mode=mode, .option=0xdead0000u + mode};
    unsigned before = refs(port), extra_before = refs(extra);
    pthread_t thread;
    assert(!pthread_create(&thread, NULL, serve, &server));
    native_status = 12345;
    bool result = (native ? darling_ca_native_query : CARenderServerGetDebugOption)(
            discovery ? MACH_PORT_NULL : port, server.option);
    assert(!pthread_join(thread, NULL));
    assert(result == (mode == 1 || mode == 2));
    if (native) {
        kern_return_t expected = mode <= 2 ? KERN_SUCCESS :
            mode == 3 || mode == 8 ? KERN_FAILURE :
            mode == 5 ? MIG_REPLY_MISMATCH : mode == 9 ? MIG_SERVER_DIED : MIG_TYPE_ERROR;
        assert(native_status == expected);
    }
    assert(refs(port) == before);
    assert(refs(extra) == extra_before);
}

static void exercise_set(mach_port_t port, mach_port_t extra, unsigned mode,
        bool native, bool discovery, bool enabled) {
    struct server server = {.port=port, .extra=extra, .mode=mode,
        .option=0x12345678, .kind=1, .enabled=enabled};
    unsigned before = refs(port), extra_before = refs(extra);
    pthread_t thread;
    assert(!pthread_create(&thread, NULL, serve, &server));
    native_status = 12345;
    (native ? darling_ca_native_set_option : CARenderServerSetDebugOption)(
        discovery ? MACH_PORT_NULL : port, server.option, enabled);
    assert(!pthread_join(thread, NULL));
    if (native) {
        kern_return_t expected = mode <= 2 ? KERN_SUCCESS :
            mode == 3 || mode == 8 ? KERN_FAILURE :
            mode == 5 ? MIG_REPLY_MISMATCH : mode == 9 ? MIG_SERVER_DIED : MIG_TYPE_ERROR;
        // Unlike a value reply, a 36-byte success reply is valid for setters.
        if (mode == 4) expected = KERN_SUCCESS;
        assert(native_status == expected);
    }
    assert(refs(port) == before && refs(extra) == extra_before);
}

static void exercise_stats(mach_port_t port, unsigned mode, bool native,
        bool discovery, const char *path, uint32_t expected) {
    FILE *file = fopen(path, "rb");
    assert(file && !fseek(file, 0, SEEK_END));
    long length = ftell(file);
    assert(length > 0 && !fseek(file, 0, SEEK_SET));
    unsigned char *bytes = malloc((size_t)length);
    assert(bytes && fread(bytes, 1, (size_t)length, file) == (size_t)length);
    fclose(file);
    struct server server = {.port=port, .kind=2, .mode=mode,
        .data=bytes, .length=(size_t)length};
    unsigned before = refs(port);
    pthread_t thread;
    assert(!pthread_create(&thread, NULL, serve, &server));
    uint32_t actual = (native ? darling_ca_native_frame_counter : CARenderServerGetFrameCounter)(
            discovery ? MACH_PORT_NULL : port);
    assert(!pthread_join(thread, NULL));
    printf("CA_STATS_VECTOR=%s MODE=%u NATIVE=%d ACTUAL=%u EXPECTED=%u\n", path, mode, native, actual, expected);
    assert(actual == expected);
    assert(refs(port) == before);
    free(bytes);
}

int main(int argc, char **argv) {
    assert(argc == 2);
    setbuf(stdout, NULL);
    mach_port_t existing = MACH_PORT_NULL;
    kern_return_t absent = bootstrap_look_up(bootstrap_port, "com.apple.CARenderServer", &existing);
    assert(absent != KERN_SUCCESS && existing == MACH_PORT_NULL);
    assert(!CARenderServerGetDebugOption(MACH_PORT_NULL, 13));
    assert(!darling_ca_native_query(MACH_PORT_NULL, 13));
    CARenderServerSetDebugOption(MACH_PORT_NULL, 13, true);
    darling_ca_native_set_option(MACH_PORT_NULL, 13, true);
    assert(!CARenderServerGetFrameCounter(MACH_PORT_NULL));
    assert(!darling_ca_native_frame_counter(MACH_PORT_NULL));
    mach_port_t port = make_port(), extra = make_port();
    for (unsigned mode = 0; mode < 10; ++mode) {
        exercise(port, extra, mode, true, false);
        exercise(port, extra, mode, false, false);
    }
    puts("CA_RENDER_REAL_MACH_WIRE_NATIVE_DIFFERENTIAL_20_EXCHANGES_OK");
    for (unsigned mode = 0; mode < 10; ++mode) {
        exercise_set(port, extra, mode, true, false, mode % 2);
        exercise_set(port, extra, mode, false, false, mode % 2);
    }
    uint32_t expected[] = {0,1,42,UINT32_MAX,UINT32_MAX,0x80000000,0x7fffffff,1,0,0,0,0,0,0,7};
    char path[1024];
    for (unsigned index = 0; index < sizeof(expected)/sizeof(expected[0]); ++index) {
        snprintf(path, sizeof(path), "%s/%u.plist", argv[1], index);
        exercise_stats(port, 0, true, false, path, expected[index]);
        exercise_stats(port, 0, false, false, path, expected[index]);
    }
    snprintf(path, sizeof(path), "%s/2.plist", argv[1]);
    for (unsigned mode = 100; mode <= 104; ++mode) {
        exercise_stats(port, mode, true, false, path, 0);
        exercise_stats(port, mode, false, false, path, 0);
    }
    // This registration is confined to the project's private Darling session.
    // The absent-service assertion above prevents replacing an existing server.
    kern_return_t registered = bootstrap_register(bootstrap_port, "com.apple.CARenderServer", port);
    printf("CA_RENDER_PRIVATE_BOOTSTRAP_REGISTER_STATUS=%d\n", registered);
    assert(registered == KERN_SUCCESS);
    for (unsigned mode = 0; mode < 3; ++mode) {
        exercise(port, extra, mode, true, true);
        exercise(port, extra, mode, false, true);
    }
    exercise_set(port, extra, 0, true, true, true);
    exercise_set(port, extra, 0, false, true, false);
    exercise_stats(port, 0, true, true, path, 42);
    exercise_stats(port, 0, false, true, path, 42);
    // This legacy launchd rejects re-registering an active service with NULL.
    // Destroy its receive right below; the entire private PID/bootstrap
    // namespace is also shut down by bin/darling after this process exits.
    assert(lookup_calls == 8);
    assert(exchanges == 90);
    mach_port_t dead = make_port();
    assert(mach_port_mod_refs(mach_task_self(), dead, MACH_PORT_RIGHT_RECEIVE, -1) == KERN_SUCCESS);
    assert(!CARenderServerGetDebugOption(dead, 77));
    assert(!darling_ca_native_query(dead, 77));
    CARenderServerSetDebugOption(dead, 77, true);
    darling_ca_native_set_option(dead, 77, true);
    assert(!CARenderServerGetFrameCounter(dead));
    assert(!darling_ca_native_frame_counter(dead));
    assert(mach_port_deallocate(mach_task_self(), dead) == KERN_SUCCESS);
    assert(mach_port_destroy(mach_task_self(), port) == KERN_SUCCESS);
    assert(mach_port_destroy(mach_task_self(), extra) == KERN_SUCCESS);
    puts("CA_RENDER_SOURCE_REAL_IPC_DISCOVERY_MALFORMED_REPLIES_DEAD_PORT_AND_RIGHTS_OK");
    puts("CA_RENDER_DEBUG_GET_SET_STATISTICS_OOL_BPLIST_NATIVE_DIFFERENTIAL_90_EXCHANGES_OK");
    return 0;
}
