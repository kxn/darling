#include <assert.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>
#include <uuid/uuid.h>
#include <servers/bootstrap.h>
#include <mach/mach.h>
#include <dlfcn.h>
#include "../../vendor/darling/src/external/libxpc/include/xpc/private/service.h"
extern int xpc_pipe_receive(mach_port_t, xpc_object_t*, uint64_t);
extern int xpc_pipe_routine_reply(xpc_object_t);

static pid_t listed_pid(const char* label) {
    FILE* stream = popen("/bin/launchctl list", "r"); assert(stream);
    char line[1024], pid[32], status[32], name[256]; pid_t result = 0;
    while (fgets(line, sizeof(line), stream)) {
        if (sscanf(line, "%31s %31s %255s", pid, status, name) == 3 && !strcmp(name, label))
            result = atoi(pid);
    }
    assert(pclose(stream) == 0); return result;
}
static unsigned records(const char* path, pid_t* latest) {
    FILE* stream = fopen(path, "r"); if (!stream) { assert(errno == ENOENT); return 0; }
    unsigned count = 0; int pid;
    while (fscanf(stream, "%d", &pid) == 1) { ++count; *latest = pid; }
    fclose(stream); return count;
}
static pid_t wait_record(const char* path, unsigned expected) {
    pid_t latest = 0;
    for (int i = 0; i < 100; ++i) {
        unsigned count = records(path, &latest);
        assert(count <= expected);
        if (count == expected) return latest;
        usleep(30000);
    }
    fprintf(stderr, "Missing job entry: %s expected %u\n", path, expected); abort();
}
static mach_port_t wait_suspended(pid_t pid) {
    mach_port_t task = MACH_PORT_NULL;
    for (int i = 0; i < 100; ++i) {
        if (!task) (void)task_for_pid(mach_task_self(), pid, &task);
        if (task) {
            struct task_basic_info_64 info;
            mach_msg_type_number_t count = TASK_BASIC_INFO_64_COUNT;
            assert(!task_info(task, TASK_BASIC_INFO_64, (task_info_t)&info, &count));
            if (info.suspend_count == 1) return task;
            assert(!info.suspend_count);
        }
        usleep(30000);
    }
    fprintf(stderr, "Job did not enter real Mach task suspension: %d\n", pid); abort();
}
static void plist(const char* executable, const char* path, const char* label, const char* marker) {
    FILE* stream = fopen(path, "w"); assert(stream); assert(!fchmod(fileno(stream), 0644));
    fprintf(stream, "<?xml version=\"1.0\"?><plist version=\"1.0\"><dict>"
        "<key>Label</key><string>%s</string><key>ProgramArguments</key><array>"
        "<string>%s</string><string>--job</string><string>%s</string></array>"
        "<key>RunAtLoad</key><false/></dict></plist>", label, executable, marker);
    assert(!fclose(stream));
    char command[1600]; snprintf(command, sizeof(command), "/bin/launchctl load '%s'", path);
    assert(!system(command));
}
static void unload(const char* path) {
    char command[1600]; snprintf(command, sizeof(command), "/bin/launchctl unload '%s'", path);
    assert(!system(command)); assert(!unlink(path));
}
static xpc_object_t service(const char* label) {
    char specifier[512]; snprintf(specifier, sizeof(specifier), "system/%s", label);
    dispatch_queue_t queue = dispatch_queue_create("test.service.owner", NULL);
    xpc_object_t object = xpc_service_create_from_specifier(specifier, queue); assert(object);
    dispatch_release(queue);
    assert(!strcmp(xpc_service_get_rendezvous_token(object), label)); return object;
}
static void impostor(void) {
    mach_port_t receiver;
    assert(!mach_port_allocate(mach_task_self(), MACH_PORT_RIGHT_RECEIVE, &receiver));
    assert(!mach_port_insert_right(mach_task_self(), receiver, receiver, MACH_MSG_TYPE_MAKE_SEND));
    char name[] = "org.linuxcode.xpc-service-impostor";
    assert(!bootstrap_register(bootstrap_port, name, receiver));
    pid_t child = fork(); assert(child >= 0);
    if (!child) {
        mach_port_t fake; assert(!bootstrap_look_up(bootstrap_port, name, &fake)); bootstrap_port = fake;
        xpc_object_t object = service("test.native-envelope");
        assert(xpc_service_kickstart_with_flags(object, 3) == EPERM);
        xpc_release(object); _exit(0);
    }
    xpc_object_t request = NULL; assert(!xpc_pipe_receive(receiver, &request, 0) && request);
    assert(xpc_dictionary_get_uint64(request, "subsystem") == 2);
    assert(xpc_dictionary_get_uint64(request, "routine") == 702);
    assert(xpc_dictionary_get_uint64(request, "type") == 1);
    assert(xpc_dictionary_get_uint64(request, "handle") == 0);
    assert(!strcmp(xpc_dictionary_get_string(request, "name"), "test.native-envelope"));
    assert(xpc_dictionary_get_bool(request, "unidomain"));
    assert(xpc_dictionary_get_bool(request, "suspended"));
    assert(xpc_dictionary_get_bool(request, "kill"));
    assert(xpc_dictionary_get_bool(request, "unthrottle"));
    xpc_object_t reply = xpc_dictionary_create_reply(request); assert(reply);
    xpc_dictionary_set_int64(reply, "error", 0);
    xpc_dictionary_set_int64(reply, "pid", 1); xpc_dictionary_set_int64(reply, "euid", 0);
    assert(!xpc_pipe_routine_reply(reply)); xpc_release(reply); xpc_release(request);
    int status; assert(waitpid(child, &status, 0) == child && WIFEXITED(status) && !WEXITSTATUS(status));
    assert(!mach_port_destroy(mach_task_self(), receiver));
    puts("XPC_SERVICE_NATIVE_ENVELOPE_AND_REAL_AUDIT_REJECT_FORGED_PID1_REPLY_OK");
}
static void object_contract(void) {
    const char* invalid[] = {"", "system", "system/", "user/no/name", "pid/-1/name", "other/0/name",
        "pid/9223372036854775807/name", "pid/18446744073709551616/name", "gui/1/"};
    for (unsigned i = 0; i < sizeof(invalid)/sizeof(*invalid); ++i)
        assert(!xpc_service_create_from_specifier(invalid[i], NULL));
    assert(!xpc_service_create_from_specifier(NULL, NULL));
    for (int i = 0; i < 128; ++i) {
        xpc_object_t object = xpc_service_create(2, NULL, 0, NULL); assert(object);
        uuid_t uuid; assert(!uuid_parse(xpc_service_get_rendezvous_token(object), uuid));
        xpc_retain(object); xpc_release(object);
        assert(strlen(xpc_service_get_rendezvous_token(object)) == 36); xpc_release(object);
    }
    assert(xpc_service_kickstart_with_flags(NULL, 0) == EINVAL);
    xpc_object_t wrong = xpc_dictionary_create(NULL, NULL, 0);
    assert(xpc_service_kickstart_with_flags(wrong, 0) == EINVAL); xpc_release(wrong);
    puts("XPC_SERVICE_REAL_OBJECT_QUEUE_OWNERSHIP_UUID_AND_SPECIFIER_LIFECYCLE_OK");
}
static xpc_object_t request(void) {
    xpc_object_t value = xpc_dictionary_create(NULL, NULL, 0);
    xpc_dictionary_set_uint64(value, "type", 1); xpc_dictionary_set_uint64(value, "handle", 0);
    xpc_dictionary_set_string(value, "name", "org.linuxcode.nonexistent");
    xpc_dictionary_set_bool(value, "unidomain", true);
    xpc_dictionary_set_bool(value, "suspended", false); xpc_dictionary_set_bool(value, "kill", false);
    return value;
}
static void control_errors(void) {
    xpc_object_t value = request(), reply = NULL;
    xpc_dictionary_set_string(value, "handle", "0");
    assert(_xpc_service_routine(702, value, &reply) == EINVAL && !reply); xpc_release(value);
    value = request(); xpc_dictionary_set_bool(value, "unidomain", false);
    assert(_xpc_service_routine(702, value, &reply) == EINVAL && !reply); xpc_release(value);
    value = request(); xpc_dictionary_set_uint64(value, "suspended", 1);
    assert(_xpc_service_routine(702, value, &reply) == EINVAL && !reply); xpc_release(value);
    value = request();
    assert(_xpc_service_routine(999, value, &reply) == ENOTSUP && !reply); xpc_release(value);
    puts("XPC_SERVICE_REAL_LAUNCHD_MALFORMED_TYPED_REQUESTS_AND_UNSUPPORTED_ROUTINE_ERRORS_OK");
}
int main(int argc, char** argv) {
    setbuf(stdout, NULL);
    if (argc == 3 && !strcmp(argv[1], "--job")) {
        FILE* stream = fopen(argv[2], "a"); assert(stream);
        fprintf(stream, "%d\n", getpid()); assert(!fclose(stream));
        for (;;) pause();
    }
    if (argc == 2 && !strcmp(argv[1], "--timeout")) {
        xpc_object_t object = service("org.linuxcode.incompatible-launchd");
        int error = xpc_service_kickstart_with_flags(object, 0);
        fprintf(stderr, "Incompatible launchd service error: %d\n", error);
        assert(error == ETIMEDOUT);
        xpc_release(object); puts("XPC_SERVICE_INCOMPATIBLE_LAUNCHD_REAL_TIMEOUT_OK"); return 0;
    }
    assert(argc == 2);
    Dl_info service_owner, base_owner;
    assert(dladdr((void*)xpc_service_kickstart_with_flags, &service_owner));
    assert(dladdr((void*)xpc_release, &base_owner));
    assert(service_owner.dli_fbase == base_owner.dli_fbase);
    puts("XPC_SERVICE_API_OWNED_BY_ACTUAL_LIBXPC_BACKEND_OK");
    object_contract(); impostor(); control_errors();
    char label[256], path[1024], marker[1024];
    snprintf(label, sizeof(label), "org.linuxcode.service.%d", getpid());
    snprintf(path, sizeof(path), "%s/%s.plist", argv[1], label);
    snprintf(marker, sizeof(marker), "%s/%s.entries", argv[1], label);
    unlink(marker); plist(argv[0], path, label, marker);
    assert(!listed_pid(label)); xpc_object_t object = service(label);
    assert(!xpc_service_kickstart_with_flags(object, 0));
    pid_t previous = wait_record(marker, 1); assert(previous > 1 && !kill(previous, 0));
    assert(!xpc_service_kickstart(object, false, false));
    assert(!xpc_service_kickstart_with_flags(object, 1ULL << 63));
    assert(!xpc_service_kickstart_with_flags(object, 1));
    pid_t latest = 0; assert(records(marker, &latest) == 1 && latest == previous);
    mach_port_t running_task;
    assert(!task_for_pid(mach_task_self(), previous, &running_task));
    struct task_basic_info_64 running_info; mach_msg_type_number_t count = TASK_BASIC_INFO_64_COUNT;
    assert(!task_info(running_task, TASK_BASIC_INFO_64, (task_info_t)&running_info, &count));
    assert(!running_info.suspend_count); assert(!mach_port_deallocate(mach_task_self(), running_task));
    for (unsigned i = 2; i <= 9; ++i) {
        assert(!xpc_service_kickstart_with_flags(object, 2));
        latest = wait_record(marker, i); assert(latest > 1 && latest != previous);
        assert(kill(previous, 0) == -1 && errno == ESRCH);
        assert(!kill(latest, 0)); assert(listed_pid(label) == latest); previous = latest;
    }
    puts("XPC_SERVICE_REAL_LAUNCHD_START_REPEAT_AND_EIGHT_WAIT4_RESTARTS_OK");
    assert(!xpc_service_kickstart(object, true, true));
    pid_t suspended = listed_pid(label); assert(suspended > 1 && suspended != previous);
    mach_port_t task = wait_suspended(suspended);
    usleep(300000); assert(records(marker, &latest) == 9 && latest == previous);
    assert(kill(previous, 0) == -1 && errno == ESRCH);
    assert(!task_resume(task)); assert(!mach_port_deallocate(mach_task_self(), task));
    assert(wait_record(marker, 10) == suspended);
    puts("XPC_SERVICE_REAL_RESTART_SUSPENDS_BEFORE_USER_ENTRY_AND_TASK_RESUME_WORKS_OK");
    xpc_release(object); unload(path); unlink(marker);

    snprintf(label, sizeof(label), "org.linuxcode.suspended.%d", getpid());
    snprintf(path, sizeof(path), "%s/%s.plist", argv[1], label);
    snprintf(marker, sizeof(marker), "%s/%s.entries", argv[1], label);
    unlink(marker); plist(argv[0], path, label, marker); object = service(label);
    assert(!xpc_service_kickstart_with_flags(object, 1));
    suspended = listed_pid(label); assert(suspended > 1);
    task = wait_suspended(suspended);
    usleep(300000); assert(records(marker, &latest) == 0);
    assert(!task_resume(task)); assert(!mach_port_deallocate(mach_task_self(), task));
    assert(wait_record(marker, 1) == suspended);
    xpc_release(object); unload(path); unlink(marker);
    puts("XPC_SERVICE_REAL_COLD_START_SUSPENSION_OK");

    object = service("org.linuxcode.nonexistent"); assert(xpc_service_kickstart_with_flags(object, 0) == ESRCH);
    xpc_release(object);
    object = xpc_service_create_from_specifier("user/0/org.linuxcode.test", NULL); assert(object);
    assert(xpc_service_kickstart_with_flags(object, 0) == ENOTSUP); xpc_release(object);
    object = xpc_service_create(1, "org.linuxcode.test", getpid(), NULL); assert(object);
    assert(xpc_service_kickstart_with_flags(object, 0) == ESRCH); xpc_release(object);
    object = xpc_service_create(2, "org.linuxcode.test", 0, NULL); assert(object);
    assert(xpc_service_kickstart_with_flags(object, 0) == ENOTSUP); xpc_release(object);
    pid_t child = fork(); assert(child >= 0);
    if (!child) {
        assert(!setuid(501)); object = service("org.linuxcode.nonexistent");
        assert(xpc_service_kickstart_with_flags(object, 0) == EPERM); xpc_release(object);
        xpc_object_t forged = request(), reply = NULL;
        xpc_dictionary_set_uint64(forged, "pid", 1); xpc_dictionary_set_uint64(forged, "euid", 0);
        assert(_xpc_service_routine(702, forged, &reply) == EPERM && !reply);
        xpc_release(forged); _exit(0);
    }
    int status; assert(waitpid(child, &status, 0) == child && WIFEXITED(status) && !WEXITSTATUS(status));
    puts("XPC_SERVICE_REAL_MISSING_JOB_UNSUPPORTED_DOMAINS_AND_UNPRIVILEGED_DENIAL_OK");
    return 0;
}
