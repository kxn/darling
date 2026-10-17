// Apple runtime.h enumeration contract, backed by the existing Darling objc4
// runtime's per-image and already-realized class snapshots. Never enumerate
// all images via objc_copyClassList(), which would realize every class.
#include <objc/runtime.h>
#include <mach-o/dyld.h>
#include <dlfcn.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <stdio.h>

extern Class *objc_copyClassesForImage(const char *,unsigned int *);
extern Class *objc_copyRealizedClassList(unsigned int *);

static const char *image_name(const void *image,const void *caller) {
    if (!image) {
        Dl_info info;
        return dladdr(caller,&info)?info.dli_fname:NULL;
    }
    uint32_t count=_dyld_image_count();
    for (uint32_t i=0;i<count;i++)
        if (image==_dyld_get_image_header(i))return _dyld_get_image_name(i);
    // Resolve opaque dlopen handles without reading their private storage or
    // causing another image to load. RTLD_FIRST is a distinct handle flavor.
    for (uint32_t i=0;i<count;i++) {
        const char *name=_dyld_get_image_name(i);
        for (unsigned first=0;first<2;first++) {
            void *handle=dlopen(name,RTLD_LAZY|RTLD_NOLOAD|(first?RTLD_FIRST:0));
            if (!handle)continue;
            bool same=handle==image;dlclose(handle);
            if (same)return name;
        }
    }
    return NULL;
}
static bool dynamically_registered(Class cls) {
    // Pinned Darling objc-runtime-new.h: realized class data is class_rw_t;
    // the public snapshot below guarantees the RW_REALIZED bit. Read only.
    uintptr_t data=((const uintptr_t *)(const void *)cls)[4]&UINT64_C(0x00007ffffffffff8);
    uint32_t flags=*(const uint32_t *)data;
    if (!(flags&(1u<<31))) __builtin_trap();
    return (flags&(1u<<25))!=0;
}
static bool conforms(Class cls,Protocol *protocol) {
    for (Class current=cls;current;current=class_getSuperclass(current)) {
        // Darling's older class_conformsToProtocol expects a realized class.
        // Resolve only the selected class, never the entire process registry.
        current=objc_getClass(class_getName(current));
        if (!current) return false;
        if (class_conformsToProtocol(current,protocol))return true;
    }
    return false;
}
void objc_enumerateClasses(const void *image,const char *prefix,Protocol *protocol,
                          Class superclass,void (^block)(Class,BOOL *)) {
    if (!block) { errno=EINVAL;return; }
    unsigned int count=0;
    bool dynamic=image==OBJC_DYNAMIC_CLASSES;
    const char *name=dynamic?NULL:image_name(image,__builtin_return_address(0));
    if (!dynamic && !name) { errno=EINVAL;return; }
    Class *classes=dynamic?objc_copyRealizedClassList(&count):objc_copyClassesForImage(name,&count);
    if (!classes)return;
    size_t length=prefix?strlen(prefix):0;
    BOOL stop=NO;
    for (unsigned int i=0;i<count && !stop;i++) {
        Class cls=classes[i];if (!cls)continue;
        if (dynamic && !dynamically_registered(cls))continue;
        if (prefix && strncmp(class_getName(cls),prefix,length))continue;
        if (superclass) {
            Class current=class_getSuperclass(cls);
            while (current && current!=superclass)current=class_getSuperclass(current);
            if (!current)continue;
        }
        if (protocol && !conforms(cls,protocol))continue;
        block(cls,&stop);
    }
    free(classes);
}
