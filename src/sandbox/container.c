/* Darling Intel Sandbox container-path query ABI.
 * The policy owns process identity validation and path authority. If no
 * Sandbox policy is registered, preserve the real __mac_syscall error.
 */
#include <mach/message.h>
#include <stddef.h>
#include <stdint.h>
extern int __mac_syscall(const char *, int, void *);

int sandbox_container_path_for_audit_token(audit_token_t token, char *buffer, size_t size)
{
    uint64_t arguments[5] = {token.val[5], token.val[7], (uintptr_t)buffer, size, 1};
    return __mac_syscall("Sandbox", 4, arguments);
}
