// Backport objc4 sel_lookUpByName over the pinned runtime's actual selector set.
// The existing library is unchanged. Read access uses its original selLock.
#include <objc/runtime.h>
#include <os/lock.h>
#include <mach-o/loader.h>
#include <dlfcn.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include "selector-backend.h"

extern const char *_dyld_get_objc_selector(const char *);
struct SelectorSet { const char **buckets; uint32_t entries,tombstones,bucketCount; };
_Static_assert(sizeof(struct SelectorSet)==24,"Pinned DenseSet storage");
_Static_assert(sizeof(os_unfair_lock)==4,"Pinned objc mutex storage");

static void incompatible(void) {
    fputs("Objective-C selector backend UUID/code/layout guard rejected incompatible runtime\n",stderr);
    __builtin_trap();
}
static uintptr_t backend(void) {
    Dl_info info;
    if (!dladdr((void *)sel_isMapped,&info))incompatible();
    uintptr_t base=(uintptr_t)info.dli_fbase;
    if ((uintptr_t)sel_isMapped!=base+selector_probe_offset ||
        memcmp((void *)sel_isMapped,selector_probe_bytes,sizeof(selector_probe_bytes)))incompatible();
    const struct mach_header_64 *header=(void *)base;
    if (header->magic!=MH_MAGIC_64 || header->ncmds>4096)incompatible();
    const unsigned char *cursor=(void *)(header+1),*end=cursor+header->sizeofcmds;
    bool found=false;
    for (uint32_t i=0;i<header->ncmds;i++) {
        if (cursor+sizeof(struct load_command)>end)incompatible();
        const struct load_command *command=(void *)cursor;
        if (command->cmdsize<8 || cursor+command->cmdsize>end)incompatible();
        if (command->cmd==LC_UUID) {
            if (command->cmdsize!=24 || memcmp(cursor+8,selector_backend_uuid,16))incompatible();
            found=true;
        }
        cursor+=command->cmdsize;
    }
    if (!found)incompatible();
    return base;
}
SEL sel_lookUpByName(const char *name) {
    if (!name)return NULL;
    uintptr_t base=backend();
    const char *builtin=_dyld_get_objc_selector(name);
    if (builtin)return (SEL)(void *)builtin;
    os_unfair_lock *lock=(void *)(base+selector_lock_offset);
    const struct SelectorSet *set=(void *)(base+selector_set_offset);
    SEL result=NULL;
    os_unfair_lock_lock(lock);
    uint32_t count=set->bucketCount;
    if (count) {
        if ((count&(count-1)) || count>(1u<<28) || !set->buckets || set->entries>count || set->tombstones>count)
            incompatible();
        uint32_t bucket=_objc_strhash(name)&(count-1);
        for (uint32_t probe=1;probe<=count+1;probe++) {
            const char *candidate=set->buckets[bucket];
            if (candidate==(const char *)UINTPTR_MAX)break;
            if (candidate && candidate!=(const char *)(UINTPTR_MAX-1) && !strcmp(candidate,name)) {
                result=(SEL)(void *)candidate;break;
            }
            if (probe>count)incompatible();
            bucket=(bucket+probe)&(count-1);
        }
    }
    os_unfair_lock_unlock(lock);
    return result;
}
