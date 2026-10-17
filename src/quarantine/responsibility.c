/*
 * Darling - libquarantine
 *
 * This library is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License, version 3 or later.
 * This library is distributed without any warranty. See LICENSE.
 */
#include "include/responsibility.h"
#include <errno.h>
#include <pthread.h>
#include <stdlib.h>
#include <string.h>

extern int posix_spawnattr_getmacpolicyinfo_np(const posix_spawnattr_t*, const char*, void**, size_t*);
extern int posix_spawnattr_setmacpolicyinfo_np(posix_spawnattr_t*, const char*, void*, size_t);
extern int __mac_syscall(const char*, int, void*);

struct quarantine_spawn_data {
    uint32_t version;
    uint32_t size;
    uint32_t flags;
    uint32_t reserved;
    uint64_t extra;
};
_Static_assert(sizeof(struct quarantine_spawn_data) == 24, "Quarantine spawn ABI");
static pthread_once_t spawn_once = PTHREAD_ONCE_INIT;
static pthread_key_t spawn_key;
static int spawn_key_error;

static void make_spawn_key(void)
{
    spawn_key_error = pthread_key_create(&spawn_key, free);
}

int responsibility_spawnattrs_setdisclaim(posix_spawnattr_t* attrs, bool disclaim)
{
    struct quarantine_spawn_data* data = NULL;
    size_t length = sizeof(*data);
    int error = posix_spawnattr_getmacpolicyinfo_np(attrs, "Quarantine", (void**)&data, &length);
    if (error == ESRCH) {
        error = pthread_once(&spawn_once, make_spawn_key);
        if (error) return error;
        if (spawn_key_error) return spawn_key_error;
        data = pthread_getspecific(spawn_key);
        if (!data) {
            data = calloc(1, sizeof(*data));
            if (!data) return ENOMEM;
            error = pthread_setspecific(spawn_key, data);
            if (error) { free(data); return error; }
        }
        // Native libquarantine borrows one buffer per thread. The MAC policy
        // descriptor does not own it, and destroying attrs must not free it.
        memset(data, 0, sizeof(*data));
        data->version = 1;
        data->size = sizeof(*data);
    } else if (error) return error;
    if (length != sizeof(*data) || !data) return EINVAL;
    data->flags = (data->flags & ~1u) | (disclaim ? 1u : 0u);
    return posix_spawnattr_setmacpolicyinfo_np(attrs, "Quarantine", data, sizeof(*data));
}

int responsibility_spawnattrs_getdisclaim(const posix_spawnattr_t* attrs, bool* disclaim)
{
    struct quarantine_spawn_data* data = NULL;
    size_t length = 0;
    int error = posix_spawnattr_getmacpolicyinfo_np(attrs, "Quarantine", (void**)&data, &length);
    if (error) return error;
    if (length != sizeof(*data) || !data) return EINVAL;
    if (disclaim) *disclaim = (data->flags & 1) != 0;
    return 0;
}

static int get_responsibility(pid_t pid, pid_t* responsible, uint64_t* unique)
{
    uint64_t args[5] = {(uint64_t)(int64_t)pid, (uintptr_t)responsible, (uintptr_t)unique, 0, 0};
    return __mac_syscall("Quarantine", 180, args);
}

pid_t responsibility_get_pid_responsible_for_pid(pid_t pid)
{
    pid_t result = 0;
    return get_responsibility(pid, &result, NULL) ? -1 : result;
}

uint64_t responsibility_get_uniqueid_responsible_for_pid(pid_t pid)
{
    uint64_t result = 0;
    return get_responsibility(pid, NULL, &result) ? UINT64_MAX : result;
}
