#include <mach-o/dyld.h>
#include <mach-o/loader.h>
#include <dlfcn.h>
#include <assert.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
extern const struct mach_header* _dyld_get_dlopen_image_header(void*);
extern const struct mach_header* _dyld_get_image_header_containing_address(const void*);
extern const struct mach_header_64 _mh_execute_header;

static const char* empty_path;
static void check_header(const struct mach_header* h) {
    assert(h && h->magic==MH_MAGIC_64 && h->cputype==CPU_TYPE_X86_64);
}
static void* worker(void* unused) {
    for (unsigned i=0;i<64;++i) {
        void* h=dlopen(empty_path,RTLD_LAZY|RTLD_LOCAL); assert(h);
        const struct mach_header* header=_dyld_get_dlopen_image_header(h);check_header(header);
        assert(_dyld_get_image_header_containing_address(header)==header);
        assert(!dlclose(h));
    }
    return NULL;
}
static void modules(const char* path) {
    NSObjectFileImage files[2]; NSModule modules[2]; const struct mach_header* headers[2];
    for (unsigned i=0;i<2;++i) {
        assert(NSCreateObjectFileImageFromFile(path,&files[i])==NSObjectFileImageSuccess);
        modules[i]=NSLinkModule(files[i],"same-module-name",NSLINKMODULE_OPTION_PRIVATE|NSLINKMODULE_OPTION_BINDNOW);
        assert(modules[i]); headers[i]=_dyld_get_dlopen_image_header((void*)modules[i]);check_header(headers[i]);
        assert(NSNameOfModule(modules[i]));
    }
    assert(headers[0]!=headers[1]);
    assert(!strcmp(NSNameOfModule(modules[0]),NSNameOfModule(modules[1])));
    for (unsigned i=0;i<2;++i) {
        assert(_dyld_get_dlopen_image_header((void*)modules[i])==headers[i]);
        assert(NSUnLinkModule(modules[i],0));
        assert(!_dyld_get_dlopen_image_header((void*)modules[i]));
        assert(NSDestroyObjectFileImage(files[i]));
    }
    puts("DYLD_DLOPEN_HEADER_REAL_DUPLICATE_MODULE_NAMES_AND_UNLINK_INVALIDATION_OK");
}
int main(int argc,char** argv) {
    setbuf(stdout,NULL);assert(argc==4);empty_path=argv[1];
    Dl_info api_owner,base_owner;
    assert(dladdr((void*)_dyld_get_dlopen_image_header,&api_owner));
    assert(dladdr((void*)_dyld_get_image_header,&base_owner));
    assert(api_owner.dli_fbase==base_owner.dli_fbase);
    puts("DYLD_DLOPEN_HEADER_API_OWNED_BY_ACTUAL_LIBDYLD_OK");
    const struct mach_header* main=(const struct mach_header*)&_mh_execute_header;
    assert(_dyld_get_dlopen_image_header(RTLD_MAIN_ONLY)==main);
    assert(_dyld_get_dlopen_image_header(RTLD_SELF)==main);
    const uintptr_t invalid[]={0,1,2,0x1234,UINTPTR_MAX,(uintptr_t)RTLD_DEFAULT};
    for (unsigned i=0;i<sizeof(invalid)/sizeof(*invalid);++i)assert(!_dyld_get_dlopen_image_header((void*)invalid[i]));
    void* first=dlopen(empty_path,RTLD_LAZY|RTLD_LOCAL);assert(first);
    const struct mach_header* header=_dyld_get_dlopen_image_header(first);check_header(header);
    dlerror();assert(!dlsym(first,"definitely_missing_header_symbol"));
    assert(_dyld_get_dlopen_image_header(first)==header);
    const char* error=dlerror();assert(error && strstr(error,"definitely_missing_header_symbol"));assert(!dlerror());
    void* second=dlopen(empty_path,RTLD_LAZY|RTLD_FIRST);assert(second);
    assert(_dyld_get_dlopen_image_header(second)==header);
    assert(!dlclose(first));assert(_dyld_get_dlopen_image_header(second)==header);
    assert(!dlclose(second));assert(!_dyld_get_dlopen_image_header(second));
    assert(!_dyld_get_image_header_containing_address(header));
    puts("DYLD_DLOPEN_HEADER_REAL_NO_EXPORTS_FIRST_MULTIPLE_REFERENCES_UNLOAD_INVALID_HANDLES_AND_DLERROR_OK");
    void* wrapper=dlopen(argv[2],RTLD_LAZY|RTLD_LOCAL);assert(wrapper);
    const struct mach_header* wrapper_header=_dyld_get_dlopen_image_header(wrapper);check_header(wrapper_header);
    void* symbol=dlsym(wrapper,"fixture_value");assert(symbol);Dl_info owner;assert(dladdr(symbol,&owner));
    assert(wrapper_header!=owner.dli_fbase);
    const struct mach_header* (*self)(void)=dlsym(wrapper,"fixture_self_header");assert(self);
    assert(self()==owner.dli_fbase);assert(!dlclose(wrapper));
    puts("DYLD_DLOPEN_HEADER_REAL_REEXPORT_OWNER_AND_DYLIB_RTLD_SELF_CALLER_OK");
    modules(argv[3]);
    pthread_t readers[8];for (unsigned i=0;i<8;++i)assert(!pthread_create(&readers[i],NULL,worker,NULL));
    for (unsigned i=0;i<8;++i)assert(!pthread_join(readers[i],NULL));
    puts("DYLD_DLOPEN_HEADER_REAL_EIGHT_THREADS_512_DLOPEN_QUERY_DLCLOSE_CYCLES_OK");
    return 0;
}
