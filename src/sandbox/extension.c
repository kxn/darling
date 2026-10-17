/* Darling sandbox extension user-space ABI.
 * Distributed under the same APSL 2.0 terms as sandbox.h; see that file.
 */
#include "extension.h"
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

extern int __mac_syscall(const char* policy, int operation, void* arguments);

enum { EXTENSION_TOKEN_SIZE = 0x3ff0, TARGET_PID = 0x10000, TARGET_VERSION = 0x20000 };

static char* issue_file(const char* extension_class, const char* path, uint32_t flags, pid_t pid, uint32_t version)
{
    char* token = malloc(EXTENSION_TOKEN_SIZE);
    if (!token) return NULL;
    if (flags & 1) {
        // This is the original user-space unresolved-token path. It does not
        // issue a capability or call the policy, and consume("invalid") is 0.
        strlcpy(token, "invalid", EXTENSION_TOKEN_SIZE);
        return token;
    }
    uint64_t args[7] = {(uintptr_t)extension_class, 0, (uintptr_t)path, flags,
                        (uintptr_t)token, (uint64_t)(int64_t)pid, version};
    if (__mac_syscall("Sandbox", 5, args)) {
        int saved = errno;
        free(token);
        errno = saved;
        return NULL;
    }
    return token;
}

char* sandbox_extension_issue_file(const char* extension_class, const char* path, uint32_t flags)
{
    return issue_file(extension_class, path, flags & ~(TARGET_PID | TARGET_VERSION), 0, 0);
}

char* sandbox_extension_issue_file_to_process(const char* extension_class, const char* path, uint32_t flags, audit_token_t token)
{
    return issue_file(extension_class, path, flags | TARGET_PID | TARGET_VERSION, token.val[5], token.val[7]);
}

char* sandbox_extension_issue_file_to_process_by_pid(const char* extension_class, const char* path, uint32_t flags, pid_t pid)
{
    return issue_file(extension_class, path, (flags & ~(TARGET_PID | TARGET_VERSION)) | TARGET_PID, pid, 0);
}

char* sandbox_extension_issue_file_to_self(const char* extension_class, const char* path, uint32_t flags)
{
    return sandbox_extension_issue_file_to_process_by_pid(extension_class, path, flags, getpid());
}

int64_t sandbox_extension_consume(const char* token)
{
    if (!token) { errno = EINVAL; return -1; }
    if (!strcmp(token, "invalid")) return 0;
    int64_t handle = 0;
    uint64_t args[3] = {(uintptr_t)token, strlen(token) + 1, (uintptr_t)&handle};
    return __mac_syscall("Sandbox", 6, args) ? -1 : handle;
}

int sandbox_extension_release(int64_t handle)
{
    uint64_t args[3] = {(uint64_t)handle, 0, 0};
    return __mac_syscall("Sandbox", 7, args);
}
