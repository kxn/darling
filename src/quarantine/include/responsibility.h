#ifndef DARLING_RESPONSIBILITY_H
#define DARLING_RESPONSIBILITY_H
#include <stdbool.h>
#include <stdint.h>
#include <spawn.h>
#ifdef __cplusplus
extern "C" {
#endif
int responsibility_spawnattrs_setdisclaim(posix_spawnattr_t* attrs, bool disclaim);
int responsibility_spawnattrs_getdisclaim(const posix_spawnattr_t* attrs, bool* disclaim);
pid_t responsibility_get_pid_responsible_for_pid(pid_t pid);
uint64_t responsibility_get_uniqueid_responsible_for_pid(pid_t pid);
#ifdef __cplusplus
}
#endif
#endif
