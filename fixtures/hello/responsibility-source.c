#include <assert.h>
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <libproc.h>
#include <mach-o/dyld.h>
#include <mach-o/loader.h>
#include <pthread.h>
#include <spawn.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/proc_info.h>
#include <sys/wait.h>
#include <unistd.h>

extern char **environ;
extern int posix_spawnattr_getmacpolicyinfo_np(const posix_spawnattr_t*, const char*, void**, size_t*);
extern int posix_spawnattr_setmacpolicyinfo_np(posix_spawnattr_t*, const char*, void*, size_t);
extern int __mac_syscall(const char*, int, void*);

struct api {
    int (*set)(posix_spawnattr_t*, bool);
    int (*get)(const posix_spawnattr_t*, bool*);
    pid_t (*pid)(pid_t);
    uint64_t (*unique)(pid_t);
};
static struct api source_api;
static const char *executable;

static struct api load_api(void *handle) {
    struct api a = {
        dlsym(handle, "responsibility_spawnattrs_setdisclaim"),
        dlsym(handle, "responsibility_spawnattrs_getdisclaim"),
        dlsym(handle, "responsibility_get_pid_responsible_for_pid"),
        dlsym(handle, "responsibility_get_uniqueid_responsible_for_pid")};
    return a;
}

static bool uuid_matches(void *function, const char *expected) {
    Dl_info owner;
    if (!dladdr(function, &owner)) return false;
    const struct mach_header_64 *h = owner.dli_fbase;
    assert(h->magic == MH_MAGIC_64);
    const struct load_command *lc = (const void *)(h + 1);
    for (unsigned i = 0; i < h->ncmds; ++i) {
        if (lc->cmd == LC_UUID) {
            const struct uuid_command *u = (const void *)lc;
            char text[33];
            for (unsigned j = 0; j < 16; ++j) snprintf(text + j * 2, 3, "%02x", u->uuid[j]);
            return !strcmp(text, expected);
        }
        lc = (const void *)((const char *)lc + lc->cmdsize);
    }
    return false;
}

static uint64_t process_unique(pid_t pid) {
    // Private Darling/XNU PROC_PIDUNIQIDENTIFIERINFO (17) wire layout.
    struct { uint8_t uuid[16]; uint64_t unique, parent; int32_t version;
             uint32_t reserved; uint64_t reserved3, reserved4; } info = {0};
    _Static_assert(sizeof(info) == 56, "libproc unique-ID ABI");
    assert(proc_pidinfo(pid, 17, 0, &info, sizeof(info)) > 0);
    return info.unique;
}

static void wait_exit(pid_t child, int expected) {
    int status;
    assert(waitpid(child, &status, 0) == child);
    if (!WIFEXITED(status) || WEXITSTATUS(status) != expected)
        fprintf(stderr, "child %d status %#x expected exit %d\n", child, status, expected);
    assert(WIFEXITED(status) && WEXITSTATUS(status) == expected);
}

static void run_child(const posix_spawnattr_t *attr, pid_t expected, uint64_t unique, bool grandchild) {
    char pid_text[32], unique_text[32];
    snprintf(pid_text, sizeof(pid_text), "%d", expected);
    snprintf(unique_text, sizeof(unique_text), "%llu", (unsigned long long)unique);
    char *args[] = {(char *)executable, "--child", pid_text, unique_text, grandchild ? "1" : "0", NULL};
    pid_t child;
    assert(posix_spawn(&child, executable, NULL, attr, args, environ) == 0);
    wait_exit(child, 37);
}

static void compare_attributes(struct api native) {
    posix_spawnattr_t a = NULL, b = NULL;
    bool actual = true;
    assert(source_api.set(NULL, true) == native.set(NULL, true));
    assert(source_api.set(&a, true) == native.set(&b, true));
    assert(posix_spawnattr_init(&a) == 0 && posix_spawnattr_init(&b) == 0);
    assert(source_api.get(&a, &actual) == ESRCH);
    assert(native.get(&b, NULL) == ESRCH);
    for (unsigned i = 0; i < 32; ++i) {
        bool value = (i & 1) != 0;
        assert(source_api.set(&a, value) == native.set(&b, value));
        void *left, *right;
        size_t ln, rn;
        assert(posix_spawnattr_getmacpolicyinfo_np(&a, "Quarantine", &left, &ln) == 0);
        assert(posix_spawnattr_getmacpolicyinfo_np(&b, "Quarantine", &right, &rn) == 0);
        assert(ln == 24 && rn == 24 && !memcmp(left, right, 24));
        assert(source_api.get(&b, &actual) == 0 && actual == value);
        assert(native.get(&a, &actual) == 0 && actual == value);
        assert(source_api.get(&a, NULL) == native.get(&b, NULL));
    }
    uint32_t left[6] = {7, 99, 0xa4, 0x11223344, 55, 66};
    uint32_t right[6]; memcpy(right, left, sizeof(left));
    assert(posix_spawnattr_setmacpolicyinfo_np(&a, "Quarantine", left, 24) == 0);
    assert(posix_spawnattr_setmacpolicyinfo_np(&b, "Quarantine", right, 24) == 0);
    assert(source_api.set(&a, true) == native.set(&b, true));
    assert(!memcmp(left, right, 24) && left[2] == 0xa5 && left[0] == 7 && left[5] == 66);
    assert(posix_spawnattr_setmacpolicyinfo_np(&a, "Quarantine", left, 23) == 0);
    assert(posix_spawnattr_setmacpolicyinfo_np(&b, "Quarantine", right, 23) == 0);
    assert(source_api.set(&a, true) == EINVAL && native.set(&b, true) == EINVAL);
    assert(source_api.get(&a, &actual) == EINVAL && native.get(&b, &actual) == EINVAL);
    assert(posix_spawnattr_destroy(&a) == 0 && posix_spawnattr_destroy(&b) == 0);
    puts("RESPONSIBILITY_NATIVE_ATTRIBUTE_32_ROUNDTRIPS_CROSS_GETTERS_FLAGS_AND_ERRORS_MATCH_OK");
}

static void *thread_attributes(void *unused) {
    (void)unused;
    posix_spawnattr_t a, b;
    assert(posix_spawnattr_init(&a) == 0 && posix_spawnattr_init(&b) == 0);
    assert(source_api.set(&a, true) == 0);
    assert(source_api.set(&b, false) == 0);
    bool value = true;
    // Match the native per-thread borrowed-buffer semantics for distinct attrs.
    assert(source_api.get(&a, &value) == 0 && !value);
    assert(source_api.set(&a, true) == 0);
    assert(source_api.get(&b, &value) == 0 && value);
    assert(posix_spawnattr_destroy(&a) == 0 && posix_spawnattr_destroy(&b) == 0);
    return NULL;
}

int main(int argc, char **argv) {
    executable = argv[0];
    void *library = dlopen("/usr/lib/system/libquarantine.dylib", RTLD_NOW | RTLD_LOCAL);
    assert(library);
    source_api = load_api(library);
    if (!source_api.set || !source_api.get || !source_api.pid || !source_api.unique) {
        fprintf(stderr, "SOURCE_RESPONSIBILITY_LIBRARY_REJECTED\n");
        return 88;
    }
    if (argc > 1 && !strcmp(argv[1], "--child")) {
        assert(argc == 5);
        pid_t expected = atoi(argv[2]);
        uint64_t unique = strtoull(argv[3], NULL, 10);
        if (!expected) { expected = getpid(); unique = process_unique(getpid()); }
        if (source_api.pid(0) != expected || source_api.unique(0) != unique)
            fprintf(stderr, "pid=%d responsibility=%d/%llu expected=%d/%llu\n", getpid(), source_api.pid(0),
                (unsigned long long)source_api.unique(0), expected, (unsigned long long)unique);
        assert(source_api.pid(0) == expected && source_api.pid(getpid()) == expected);
        assert(source_api.unique(0) == unique && source_api.unique(getpid()) == unique);
        if (atoi(argv[4])) run_child(NULL, expected, unique, false);
        return 37;
    }
    assert(argc == 3 && uuid_matches(source_api.set, argv[1]));
    puts("RESPONSIBILITY_SOURCE_QUARANTINE_LOADED_UUID_VERIFIED"); fflush(stdout);
    void *native_library = dlopen(argv[2], RTLD_LAZY | RTLD_LOCAL);
    if (!native_library) fprintf(stderr, "native quarantine load: %s\n", dlerror());
    assert(native_library);
    struct api native = load_api(native_library);
    assert(native.set && native.get && native.pid && native.unique);
    Dl_info native_owner;
    assert(dladdr(native.set, &native_owner));
    char *native_actual = realpath(native_owner.dli_fname, NULL), *native_expected = realpath(argv[2], NULL);
    assert(native_actual && native_expected && !strcmp(native_actual, native_expected));
    free(native_actual); free(native_expected);
    compare_attributes(native);
    for (unsigned i = 0; i < 8; ++i) {
        pthread_t thread;
        assert(pthread_create(&thread, NULL, thread_attributes, NULL) == 0);
        assert(pthread_join(thread, NULL) == 0);
    }
    pid_t inherited = source_api.pid(0);
    uint64_t inherited_unique = source_api.unique(0);
    assert(inherited > 0 && inherited_unique > 0);
    // Existing libproc fails for PID 1 while reading its nonexistent parent.
    // Self-responsible spawned children below independently check their birth
    // identity against the real successful libproc query.
    if (inherited != 1) assert(inherited_unique == process_unique(inherited));
    assert(native.pid(0) == inherited && native.unique(0) == inherited_unique);
    pid_t child = fork(); assert(child >= 0);
    if (!child) {
        assert(source_api.pid(0) == inherited && source_api.unique(0) == inherited_unique);
        _exit(23);
    }
    wait_exit(child, 23);
    posix_spawnattr_t attr;
    assert(posix_spawnattr_init(&attr) == 0);
    run_child(NULL, inherited, inherited_unique, false);
    for (unsigned i = 0; i < 4; ++i) {
        assert(source_api.set(&attr, false) == 0);
        run_child(&attr, inherited, inherited_unique, false);
        assert(source_api.set(&attr, true) == 0);
        run_child(&attr, 0, 0, true);
        assert(source_api.pid(0) == inherited && source_api.unique(0) == inherited_unique);
    }
    puts("RESPONSIBILITY_REAL_FORK_SPAWN_DISCLAIM_GRANDCHILD_INHERITANCE_AND_NATIVE_QUERY_OK"); fflush(stdout);
    assert(posix_spawnattr_setflags(&attr, POSIX_SPAWN_SETEXEC) == 0);
    char *bad_args[] = {"bad", NULL};
    assert(posix_spawn(NULL, "/no-such-responsibility-program", NULL, &attr, bad_args, environ) == ENOENT);
    char path[128]; snprintf(path, sizeof(path), "/tmp/linuxcode-responsibility-invalid-%d", getpid());
    int fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0700); assert(fd >= 0);
    assert(write(fd, "\177ELF-invalid\n", 13) == 13 && close(fd) == 0);
    int error = posix_spawn(NULL, path, NULL, &attr, bad_args, environ);
    if (error != ENOEXEC) fprintf(stderr, "invalid ELF spawn error %d errno %d\n", error, errno);
    assert(error == ENOEXEC);
    assert(source_api.pid(0) == inherited && source_api.unique(0) == inherited_unique);
    // Execute in the SAME process after failed SETEXEC, without the disclaim
    // attribute, to catch any pending transaction that leaked into plain exec.
    child = fork(); assert(child >= 0);
    if (!child) {
        assert(posix_spawn(NULL, path, NULL, &attr, bad_args, environ) == ENOEXEC);
        char pid_text[32], unique_text[32];
        snprintf(pid_text, sizeof(pid_text), "%d", inherited);
        snprintf(unique_text, sizeof(unique_text), "%llu", (unsigned long long)inherited_unique);
        char *args[] = {(char *)executable, "--child", pid_text, unique_text, "0", NULL};
        execv(executable, args);
        _exit(98);
    }
    wait_exit(child, 37);
    assert(unlink(path) == 0);
    run_child(NULL, inherited, inherited_unique, false);
    child = fork(); assert(child >= 0);
    if (!child) {
        char *args[] = {(char *)executable, "--child", "0", "0", "0", NULL};
        posix_spawn(NULL, executable, NULL, &attr, args, environ);
        _exit(98);
    }
    wait_exit(child, 37);
    assert(posix_spawnattr_setflags(&attr, 0) == 0);
    uint32_t malformed[6] = {2, 24, 1, 0, 0, 0};
    assert(posix_spawnattr_setmacpolicyinfo_np(&attr, "Quarantine", malformed, 24) == 0);
    assert(posix_spawn(NULL, executable, NULL, &attr, bad_args, environ) == EINVAL);
    malformed[0] = 1; malformed[2] = 3;
    assert(posix_spawn(NULL, executable, NULL, &attr, bad_args, environ) == ENOTSUP);
    assert(posix_spawnattr_setmacpolicyinfo_np(&attr, "Quarantine", (void *)1, 24) == 0);
    assert(posix_spawn(NULL, executable, NULL, &attr, bad_args, environ) == EFAULT);
    assert(posix_spawnattr_destroy(&attr) == 0);
    uint64_t query[5] = {0, 1, 0, 0, 0};
    errno = 0; assert(__mac_syscall("Quarantine", 180, query) == -1 && errno == EFAULT);
    errno = 0; assert(__mac_syscall("Quarantine", 180, NULL) == -1 && errno == EFAULT);
    errno = 0; assert(__mac_syscall("NoSuchPolicy", 180, query) == -1 && errno == 103 /* ENOPOLICY */);
    errno = 0; assert(__mac_syscall("Quarantine", 181, query) == -1 && errno == ENOTSUP);
    errno = 0; assert(source_api.pid(INT32_MAX) == -1 && errno == ESRCH);
    assert(source_api.pid(0) == inherited && source_api.unique(0) == inherited_unique);
    puts("RESPONSIBILITY_REAL_FAILED_SETEXEC_PIPE_ROLLBACK_SUCCESSFUL_SETEXEC_AND_BAD_POINTER_ERRORS_OK");
    return 0;
}
