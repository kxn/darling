#include <sysdir.h>
#include <sys/param.h>
#include <dlfcn.h>
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef sysdir_search_path_enumeration_state (*Start)(sysdir_search_path_directory_t,sysdir_search_path_domain_mask_t);
typedef sysdir_search_path_enumeration_state (*Next)(sysdir_search_path_enumeration_state,char *);
static void single(Start start,Next next,unsigned directory,unsigned domain,const char *expected) {
    unsigned state=start(directory,domain);assert(state);
    struct { unsigned char before[16];char path[MAXPATHLEN];unsigned char after[16]; } storage;
    memset(&storage,0xa7,sizeof(storage));
    state=next(state,storage.path);assert(state);
    assert(!strcmp(storage.path,expected));
    for (unsigned i=0;i<16;i++)assert(storage.before[i]==0xa7 && storage.after[i]==0xa7);
    assert(next(state,storage.path)==0);
}
int main(int argc,char **argv) {
    assert(argc==2);
    void *library=dlopen(argv[1],RTLD_LAZY|RTLD_LOCAL);
    if (!library) { fprintf(stderr,"%s\n",dlerror());return 1; }
    Start start=(Start)dlsym(library,"sysdir_start_search_path_enumeration");
    Next next=(Next)dlsym(library,"sysdir_get_next_search_path_enumeration");assert(start && next);
    Dl_info owner;assert(dladdr((void *)start,&owner));
    char *actual=realpath(owner.dli_fname,NULL),*expected=realpath(argv[1],NULL);
    assert(actual && expected && !strcmp(actual,expected));free(actual);free(expected);
    single(start,next,SYSDIR_DIRECTORY_LIBRARY,SYSDIR_DOMAIN_MASK_USER,"~/Library");
    single(start,next,SYSDIR_DIRECTORY_LIBRARY,SYSDIR_DOMAIN_MASK_LOCAL,"/Library");
    single(start,next,SYSDIR_DIRECTORY_LIBRARY,SYSDIR_DOMAIN_MASK_NETWORK,"/Network/Library");
    single(start,next,SYSDIR_DIRECTORY_LIBRARY,SYSDIR_DOMAIN_MASK_SYSTEM,"/System/Library");
    single(start,next,SYSDIR_DIRECTORY_CACHES,SYSDIR_DOMAIN_MASK_USER,"~/Library/Caches");
    single(start,next,SYSDIR_DIRECTORY_APPLICATION_SUPPORT,SYSDIR_DOMAIN_MASK_USER,"~/Library/Application Support");
    const char *libraries[]={"~/Library","/Library","/Network/Library","/System/Library"};
    unsigned state=start(SYSDIR_DIRECTORY_LIBRARY,SYSDIR_DOMAIN_MASK_ALL),count=0;
    char path[MAXPATHLEN];
    while ((state=next(state,path))) { assert(count<4 && !strcmp(path,libraries[count]));count++; }
    assert(count==4);
    for (unsigned domain=0;domain<16;domain++) {
        state=start(SYSDIR_DIRECTORY_LIBRARY,domain);count=0;
        for (unsigned bit=0;bit<4;bit++)if (domain&(1u<<bit)) {
            state=next(state,path);assert(state && !strcmp(path,libraries[bit]));count++;
        }
        assert(next(state,path)==0);
    }
    assert(start(0,SYSDIR_DOMAIN_MASK_ALL)==0);
    assert(start(9999,SYSDIR_DOMAIN_MASK_ALL)==0);
    puts("ORIGINAL_SEARCH_PATH_ENUMERATION_DOMAINS_ORDER_MASKS_BOUNDS_AND_OWNER_OK");
    return 0;
}
