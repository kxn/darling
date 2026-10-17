#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <mach-o/dyld.h>
#include <mach-o/loader.h>
#include <signal.h>
#include <spawn.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/select.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

extern char **environ;

static bool kernel_uuid_matches(const char *expected) {
    for (uint32_t i = 0; i < _dyld_image_count(); ++i) {
        const char *name = _dyld_get_image_name(i);
        if (!name || !strstr(name, "/libsystem_kernel.dylib")) continue;
        const struct mach_header_64 *header = (const void *)_dyld_get_image_header(i);
        assert(header->magic == MH_MAGIC_64);
        const struct load_command *lc = (const void *)(header + 1);
        for (uint32_t j = 0; j < header->ncmds; ++j) {
            if (lc->cmd == LC_UUID) {
                const struct uuid_command *uuid = (const void *)lc;
                char hex[33];
                for (unsigned k = 0; k < 16; ++k) snprintf(hex + k * 2, 3, "%02x", uuid->uuid[k]);
                printf("LOADED_LIBSYSTEM_KERNEL_UUID=%s\n", hex);
                return !strcmp(hex, expected);
            }
            lc = (const void *)((const char *)lc + lc->cmdsize);
        }
    }
    return false;
}

int main(int argc, char **argv) {
    if (argc == 2 && !strcmp(argv[1], "--child")) {
        sigset_t mask;
        assert(sigprocmask(SIG_SETMASK, NULL, &mask) == 0);
        assert(sigismember(&mask, SIGUSR1) == 1);
        assert(getpgrp() == getpid());
        assert(write(STDOUT_FILENO, "SPAWN_CHILD_OK\n", 15) == 15);
        return 37;
    }
    assert(argc == 2);
    if (!kernel_uuid_matches(argv[1])) {
        fprintf(stderr, "SOURCE_KERNEL_UUID_REJECTED\n");
        return 88;
    }
    int fds[2];
    assert(pipe(fds) == 0);
    posix_spawn_file_actions_t actions;
    posix_spawnattr_t attributes;
    assert(posix_spawn_file_actions_init(&actions) == 0);
    assert(posix_spawn_file_actions_addclose(&actions, fds[0]) == 0);
    assert(posix_spawn_file_actions_adddup2(&actions, fds[1], STDOUT_FILENO) == 0);
    assert(posix_spawn_file_actions_addclose(&actions, fds[1]) == 0);
    assert(posix_spawnattr_init(&attributes) == 0);
    sigset_t mask;
    assert(sigemptyset(&mask) == 0);
    assert(sigaddset(&mask, SIGUSR1) == 0);
    assert(posix_spawnattr_setsigmask(&attributes, &mask) == 0);
    assert(posix_spawnattr_setpgroup(&attributes, 0) == 0);
    assert(posix_spawnattr_setflags(&attributes, POSIX_SPAWN_SETSIGMASK | POSIX_SPAWN_SETPGROUP) == 0);
    pid_t child = -1;
    char *child_argv[] = {argv[0], "--child", NULL};
    errno = EDOM;
    assert(posix_spawn(&child, argv[0], &actions, &attributes, child_argv, environ) == 0);
    assert(errno == EDOM);
    assert(child > 0);
    close(fds[1]);
    char text[64] = {0};
    size_t length = 0;
    for (;;) {
        ssize_t n = read(fds[0], text + length, sizeof(text) - length - 1);
        if (n < 0 && errno == EINTR) continue;
        assert(n >= 0);
        if (!n) break;
        length += n;
        assert(length < sizeof(text) - 1);
    }
    close(fds[0]);
    assert(!strcmp(text, "SPAWN_CHILD_OK\n"));
    int status;
    assert(waitpid(child, &status, 0) == child);
    assert(WIFEXITED(status) && WEXITSTATUS(status) == 37);
    assert(posix_spawnattr_destroy(&attributes) == 0);
    assert(posix_spawn_file_actions_destroy(&actions) == 0);
    child = -1;
    errno = EDOM;
    assert(posix_spawn(&child, "/no-such-source-kernel-fixture", NULL, NULL, child_argv, environ) == ENOENT);
    assert(errno == EDOM);
    const char *scripts[] = {
        "#!/bin/sh\n[ \"$1\" = argument ] || exit 99\nexit 41\n",
        "#!  /bin/sh -e\n[ \"$1\" = argument ] || exit 99\nexit 41\n",
        "[ \"$1\" = argument ] || exit 99\nexit 41\n",
    };
    for (unsigned i = 0; i < sizeof(scripts) / sizeof(scripts[0]); ++i) {
        char path[128];
        snprintf(path, sizeof(path), "/tmp/linuxcode-source-kernel-script-%d-%u", getpid(), i);
        int fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0700);
        assert(fd >= 0);
        assert(write(fd, scripts[i], strlen(scripts[i])) == (ssize_t)strlen(scripts[i]));
        assert(close(fd) == 0);
        char *script_argv[] = {path, "argument", NULL};
        assert(posix_spawn(&child, path, NULL, NULL, script_argv, environ) == 0);
        assert(waitpid(child, &status, 0) == child);
        if (!WIFEXITED(status) || WEXITSTATUS(status) != 41)
            fprintf(stderr, "script case %u wait status %#x\n", i, status);
        assert(WIFEXITED(status) && WEXITSTATUS(status) == 41);
        assert(unlink(path) == 0);
    }
    struct timeval zero = {0};
    struct timespec zero_ts = {0};
    assert(select(0, NULL, NULL, NULL, &zero) == 0);
    assert(pselect(0, NULL, NULL, NULL, &zero_ts, NULL) == 0);
    puts("SOURCE_KERNEL_REAL_SPAWN_EXEC_PIPE_SIGNAL_MASK_PGROUP_WAIT_STATUS_ERRNO_SELECT_OK");
    puts("SOURCE_KERNEL_REAL_SHEBANG_WHITESPACE_INTERPRETER_ARGUMENT_AND_TEXT_FALLBACK_OK");
    return 0;
}
