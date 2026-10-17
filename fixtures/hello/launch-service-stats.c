#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <mach/mach_vm.h>
#include <servers/bootstrap.h>
#include <unistd.h>
#include <xpc/xpc.h>
#include "../../vendor/darling/src/external/libxpc/include/xpc/private/launch_service_stats.h"
extern xpc_object_t xpc_shmem_create_readonly(const void*, size_t);
extern int xpc_pipe_receive(mach_port_t, xpc_object_t*, uint64_t);
extern int xpc_pipe_routine_reply(xpc_object_t);

static void impostor(void) {
    const char* service = "org.linuxcode.launch-stats-impostor";
    mach_port_t receiver;
    assert(mach_port_allocate(mach_task_self(), MACH_PORT_RIGHT_RECEIVE, &receiver) == KERN_SUCCESS);
    assert(mach_port_insert_right(mach_task_self(), receiver, receiver, MACH_MSG_TYPE_MAKE_SEND) == KERN_SUCCESS);
    assert(bootstrap_register(bootstrap_port, (char*)service, receiver) == KERN_SUCCESS);
    pid_t child = fork(); assert(child >= 0);
    if (!child) {
        mach_port_t fake;
        assert(bootstrap_look_up(bootstrap_port, (char*)service, &fake) == KERN_SUCCESS);
        bootstrap_port = fake;
        assert(launch_service_stats_enable("forged-peer", 8) == EPERM);
        _exit(0);
    }
    xpc_object_t request = NULL;
    assert(!xpc_pipe_receive(receiver, &request, 0) && request);
    xpc_object_t reply = xpc_dictionary_create_reply(request); assert(reply);
    xpc_dictionary_set_int64(reply, "error", 0);
    xpc_dictionary_set_uint64(reply, "pid", 1);
    xpc_dictionary_set_uint64(reply, "euid", 0);
    assert(!xpc_pipe_routine_reply(reply));
    xpc_release(reply); xpc_release(request);
    int status; assert(waitpid(child, &status, 0) == child && WIFEXITED(status) && !WEXITSTATUS(status));
    assert(mach_port_destroy(mach_task_self(), receiver) == KERN_SUCCESS);
    puts("LAUNCH_STATS_REAL_MACH_AUDIT_REJECTS_NON_PID1_PEER_WITH_FORGED_DICTIONARY_CREDENTIALS_OK");
}

static void dispose(struct launch_service_stats* result) {
    if (result->labels) xpc_release(result->labels);
    free(result->records); memset(result, 0, sizeof(*result));
}
static void run_job(const char* directory, unsigned sequence, bool signaled, char* label, size_t capacity) {
    snprintf(label, capacity, "org.linuxcode.stats.%d.%u", getpid(), sequence);
    char path[1024], command[1200];
    snprintf(path, sizeof(path), "%s/%s.plist", directory, label);
    FILE* file = fopen(path, "w"); assert(file);
    assert(!fchmod(fileno(file), 0644));
    fprintf(file, "<?xml version=\"1.0\"?><plist version=\"1.0\"><dict>"
        "<key>Label</key><string>%s</string><key>ProgramArguments</key><array>"
        "<string>/bin/sh</string><string>-c</string><string>%s</string></array>"
        "<key>RunAtLoad</key><true/></dict></plist>", label, signaled ? "kill -ABRT $$" : "exit 7");
    assert(!fclose(file));
    snprintf(command, sizeof(command), "/bin/launchctl load '%s'", path);
    int status = system(command);
    if (status) fprintf(stderr, "launchctl load failed: %s status=%d\n", path, status);
    assert(status == 0);
}
static void remove_job(const char* directory, const char* label) {
    char path[1024], command[1200];
    snprintf(path, sizeof(path), "%s/%s.plist", directory, label);
    snprintf(command, sizeof(command), "/bin/launchctl unload '%s'", path);
    assert(system(command) == 0); assert(!unlink(path));
}
static void wait_for_job_exit(const char* label) {
    for (unsigned attempt = 0; attempt < 100; ++attempt) {
        FILE* list = popen("/bin/launchctl list", "r"); assert(list);
        char line[1024], pid[32], status[32], name[256]; bool reaped = false;
        while (fgets(line, sizeof(line), list)) {
            if (sscanf(line, "%31s %31s %255s", pid, status, name) == 3
                && !strcmp(name, label) && !strcmp(pid, "-") && !strcmp(status, "7")) reaped = true;
        }
        assert(pclose(list) == 0);
        if (reaped) return;
        usleep(50000);
    }
    fprintf(stderr, "launchd did not finish reaping %s\n", label); abort();
}
static void overflow(const char* directory, const char* monitor) {
    assert(!launch_service_stats_enable(monitor, 2));
    char labels[4][256];
    for (unsigned i = 0; i < 4; ++i) {
        run_job(directory, 100 + i, false, labels[i], sizeof(labels[i]));
        wait_for_job_exit(labels[i]);
    }
    struct launch_service_stats result = {0};
    assert(!_launch_service_stats_copy_impl(monitor, 8, &result, 6));
    assert(result.count == 2 && result.dropped_count == 2 && xpc_array_get_count(result.labels) == 2);
    for (unsigned i = 0; i < 2; ++i) {
        struct launch_service_stats_record record;
        memcpy(&record, (char*)result.records + i * 59, 59);
        assert(!strcmp(xpc_array_get_string(result.labels, record.label_index), labels[i + 2]));
    }
    dispose(&result);
    assert(!_launch_service_stats_copy_impl(monitor, 8, &result, 6));
    assert(!result.count && !result.dropped_count && !xpc_array_get_count(result.labels));
    dispose(&result);
    assert(!launch_service_stats_disable(monitor));
    for (unsigned i = 0; i < 4; ++i) remove_job(directory, labels[i]);
    puts("LAUNCH_STATS_REAL_JOB_RING_OVERFLOW_NEWEST_RECORDS_DROP_COUNT_AND_RESET_OK");
}
static void bad_requests(const char* monitor) {
    xpc_object_t request = xpc_dictionary_create(NULL, NULL, 0), reply = NULL;
    xpc_dictionary_set_string(request, "monitor_id", monitor);
    assert(_xpc_control_routine(0xffff, request, &reply) == ENOTSUP && !reply);
    xpc_dictionary_set_string(request, "monitor_id", "");
    assert(_xpc_control_routine(XPC_LAUNCH_STATS_ENABLE, request, &reply) == EINVAL && !reply);
    xpc_dictionary_set_string(request, "monitor_id", "org.linuxcode.invalid-capacity");
    xpc_dictionary_set_uint64(request, "capacity", UINT32_MAX);
    assert(_xpc_control_routine(XPC_LAUNCH_STATS_ENABLE, request, &reply) == EINVAL && !reply);
    xpc_dictionary_set_string(request, "monitor_id", monitor);
    assert(_xpc_control_routine(XPC_LAUNCH_STATS_COPY, request, &reply) == EINVAL && !reply);
    mach_vm_address_t buffer = 0;
    assert(mach_vm_allocate(mach_task_self(), &buffer, 4096, VM_FLAGS_ANYWHERE) == KERN_SUCCESS);
    xpc_object_t readonly = xpc_shmem_create_readonly((void*)buffer, 4096); assert(readonly);
    xpc_dictionary_set_value(request, "shmem", readonly); xpc_release(readonly);
    assert(_xpc_control_routine(XPC_LAUNCH_STATS_COPY, request, &reply) == EACCES && !reply);
    // An invalid or read-only request must not kill launchd or disable monitoring.
    assert(launch_service_stats_is_enabled(monitor));
    xpc_release(request); assert(!munmap((void*)buffer, 4096));
    puts("LAUNCH_STATS_REAL_CONTROL_ERRORS_AND_READONLY_BUFFER_REJECTION_OK");
}
static void live_record(const char* monitor, const char* directory, unsigned version, bool signaled) {
    static const size_t strides[] = {37,45,49,51,59};
    char label[256]; run_job(directory, version, signaled, label, sizeof(label));
    bool found = false;
    for (unsigned attempt = 0; attempt < 100 && !found; ++attempt) {
        struct launch_service_stats result = {0};
        int error = _launch_service_stats_copy_impl(monitor, 32, &result, version);
        if (error) fprintf(stderr, "stats copy error=%d (%s)\n", error, strerror(error));
        assert(!error && result.labels && xpc_get_type(result.labels) == XPC_TYPE_ARRAY);
        for (uint32_t i = 0; i < result.count; ++i) {
            struct launch_service_stats_record record = {0};
            memcpy(&record, (char*)result.records + i * strides[version - 2], strides[version - 2]);
            assert(record.label_index < xpc_array_get_count(result.labels));
            const char* name = xpc_array_get_string(result.labels, record.label_index);
            assert(name && record.pid > 0 && record.start_time);
            if (!strcmp(name, label)) {
                int wait_status = record.wait_status;
                if (signaled) {
                    assert(WIFSIGNALED(wait_status) && WTERMSIG(wait_status) == SIGABRT);
                    assert(record.reason_namespace == 2 && record.reason_code == SIGABRT);
                } else {
                    assert(WIFEXITED(wait_status) && WEXITSTATUS(wait_status) == 7);
                    assert(!record.reason_namespace && !record.reason_code);
                }
                found = true;
                printf("LAUNCH_STATS_LIVE_RECORD version=%u pid=%d status=%u namespace=%u code=%llu label=%s\n",
                    version, record.pid, record.wait_status, record.reason_namespace,
                    (unsigned long long)record.reason_code, name);
            }
        }
        dispose(&result);
        if (!found) usleep(50000);
    }
    assert(found); remove_job(directory, label);
}
int main(int argc, char** argv) {
    assert(argc == 2); setbuf(stdout, NULL);
    if (!strcmp(argv[1], "--timeout")) {
        int error = launch_service_stats_enable("org.linuxcode.incompatible-launchd", 8);
        assert(error == ETIMEDOUT);
        puts("LAUNCH_STATS_INCOMPATIBLE_PACKAGED_LAUNCHD_RETURNS_REAL_RECEIVE_TIMEOUT_OK");
        return 0;
    }
    char monitor[256]; snprintf(monitor, sizeof(monitor), "org.linuxcode.monitor.%d", getpid());
    assert(!launch_service_stats_is_enabled(monitor));
    int error = launch_service_stats_enable(monitor, 32);
    printf("LAUNCH_STATS_ENABLE status=%d (%s)\n", error, strerror(error));
    assert(!error && launch_service_stats_is_enabled(monitor));
    assert(launch_service_stats_enable(monitor, 32) == EEXIST);
    bad_requests(monitor);
    struct launch_service_stats empty = {0};
    assert(!_launch_service_stats_copy_impl(monitor, 32, &empty, 6));
    assert(!empty.count && !empty.records && empty.labels);
    dispose(&empty);
    for (unsigned version = 2; version <= 6; ++version) live_record(monitor, argv[1], version, false);
    live_record(monitor, argv[1], 6, true);
    assert(!launch_service_stats_disable(monitor));
    assert(!launch_service_stats_is_enabled(monitor));
    assert(launch_service_stats_disable(monitor) == ENOENT);
    assert(_launch_service_stats_copy_impl(monitor, 32, &empty, 6) == ENOENT);
    assert(_launch_service_stats_copy_impl(monitor, 32, &empty, 1) == EINVAL);
    assert(_launch_service_stats_copy_impl(monitor, 32, &empty, 7) == EINVAL);
    assert(_launch_service_stats_copy_impl(monitor, UINT32_MAX, &empty, 6) == ENOMEM);
    char overflow_monitor[256]; snprintf(overflow_monitor, sizeof(overflow_monitor), "%s.overflow", monitor);
    overflow(argv[1], overflow_monitor);
    impostor();
    puts("LAUNCH_STATS_REAL_LAUNCHD_WAIT4_JOBS_VERSIONS_2_TO_6_SIGNAL_REASON_AND_MONITOR_LIFECYCLE_OK");
    return 0;
}
