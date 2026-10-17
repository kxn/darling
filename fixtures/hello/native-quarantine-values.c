#include <dlfcn.h>
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
typedef void *(*Alloc)(void);
typedef void *(*Clone)(void *);
typedef void (*Free)(void *);
typedef int (*Set)(void *,uint32_t);
typedef uint32_t (*Get)(void *);
int main(int argc,char **argv) {
    assert(argc==2);
    void *library=dlopen(argv[1],RTLD_LAZY|RTLD_LOCAL);
    if (!library) { fprintf(stderr,"%s\n",dlerror());return 1; }
    Alloc allocate=(Alloc)dlsym(library,"_qtn_file_alloc");
    Clone clone=(Clone)dlsym(library,"_qtn_file_clone");
    Free release=(Free)dlsym(library,"_qtn_file_free");
    Set set=(Set)dlsym(library,"_qtn_file_set_flags");
    Get get=(Get)dlsym(library,"_qtn_file_get_flags");assert(allocate && clone && release && set && get);
    Dl_info owner;assert(dladdr((void *)allocate,&owner));
    char *actual=realpath(owner.dli_fname,NULL),*expected=realpath(argv[1],NULL);
    assert(actual && expected && !strcmp(actual,expected));free(actual);free(expected);
    for (unsigned i=0;i<257;i++) {
        uint32_t flags=i==256?0x1fff:i;
        void *file=allocate();assert(file && get(file)==0);
        assert(set(file,flags)==0 && get(file)==flags);
        void *copy=clone(file);assert(copy && copy!=file && get(copy)==flags);
        assert(set(file,flags^1)==0 && get(file)==(flags^1) && get(copy)==flags);
        assert(set(file,0x2000)==EINVAL && get(file)==(flags^1));
        assert(set(file,UINT32_MAX)==EINVAL && get(file)==(flags^1));
        release(file);assert(get(copy)==flags);release(copy);
    }
    puts("ORIGINAL_QUARANTINE_ALLOC_FLAGS_RANGE_CLONE_INDEPENDENCE_AND_RELEASE_OK");
    return 0;
}
