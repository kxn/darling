#include <sys/types.h>
#include <mach-o/loader.h>
#include <dlfcn.h>
#include <malloc/malloc.h>
#include <pthread.h>
#include <sched.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "libc-backend.h"

static void incompatible(void) {
    fputs("Foundation libc backend UUID/code guard rejected incompatible runtime\n",stderr);
    __builtin_trap();
}
static uintptr_t backend(void) {
    Dl_info info;
    if (!dladdr((void *)getenv,&info))incompatible();
    uintptr_t base=(uintptr_t)info.dli_fbase;
    if ((uintptr_t)getenv!=base+libc_probe_offset ||
        memcmp((void *)getenv,libc_probe_bytes,sizeof(libc_probe_bytes)))incompatible();
    const struct mach_header_64 *header=(void *)base;
    if (header->magic!=MH_MAGIC_64 || header->ncmds>4096)incompatible();
    const unsigned char *cursor=(void *)(header+1),*end=cursor+header->sizeofcmds;
    bool found=false;
    for (uint32_t i=0;i<header->ncmds;i++) {
        if (cursor+sizeof(struct load_command)>end)incompatible();
        const struct load_command *command=(void *)cursor;
        if (command->cmdsize<8 || cursor+command->cmdsize>end)incompatible();
        if (command->cmd==LC_UUID) {
            if (command->cmdsize!=24 || memcmp(cursor+8,libc_backend_uuid,16))incompatible();
            found=true;
        }
        cursor+=command->cmdsize;
    }
    if (!found || memcmp((void *)(base+environment_lock_offset),environment_lock_bytes,sizeof(environment_lock_bytes)) ||
        memcmp((void *)(base+environment_unlock_offset),environment_unlock_bytes,sizeof(environment_unlock_bytes)))incompatible();
    return base;
}
void environ_lock_np(void) { ((void (*)(void))(backend()+environment_lock_offset))(); }
void environ_unlock_np(void) { ((void (*)(void))(backend()+environment_unlock_offset))(); }

extern int csops(pid_t,unsigned int,void *,size_t);
int _atexit_receipt(void) {
    uint32_t category=0;
    // The native routine returns zero when this query is unsupported, as on
    // older kernels. Never use Darling's placeholder CS_OPS_STATUS result to
    // manufacture a validated signing category.
    if (!csops(0,17,&category,sizeof(category)) && category==4) {
        fputs("Darling libc does not support the native App Store exit mode\n",stderr);
        abort();
    }
    return 0;
}

// Exact SDK back-deployment fallback: allocation type IDs are hints; preserve
// the existing allocator and zone argument rather than inventing a zone.
extern void *legacy_zone_malloc(malloc_zone_t *,size_t) __asm__("_malloc_zone_malloc");
extern void *legacy_zone_calloc(malloc_zone_t *,size_t,size_t) __asm__("_malloc_zone_calloc");
extern void *legacy_zone_realloc(malloc_zone_t *,void *,size_t) __asm__("_malloc_zone_realloc");
void *malloc_type_zone_malloc(malloc_zone_t *zone,size_t size,uint64_t type) {
    return legacy_zone_malloc(zone,size);
}
void *malloc_type_zone_calloc(malloc_zone_t *zone,size_t count,size_t size,uint64_t type) {
    return legacy_zone_calloc(zone,count,size);
}
void *malloc_type_zone_realloc(malloc_zone_t *zone,void *pointer,size_t size,uint64_t type) {
    return legacy_zone_realloc(zone,pointer,size);
}
void pthread_yield_np(void) { (void)sched_yield(); }
