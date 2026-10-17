#include <assert.h>
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sysdir.h>
typedef sysdir_search_path_enumeration_state (*start_fn)(sysdir_search_path_directory_t,sysdir_search_path_domain_mask_t);
typedef sysdir_search_path_enumeration_state (*next_fn)(sysdir_search_path_enumeration_state,char *);
static unsigned cases, paths, private_differences;
static void compare(start_fn start,next_fn next,start_fn original,next_fn original_next,unsigned dir,unsigned mask) {
    unsigned a=start(dir,mask),b=original(dir,mask);assert(a==b);
    for(unsigned n=0;n<256;n++) {
        struct {uint64_t before;char path[1024];uint64_t after;} x,y;
        memset(&x,0xa7,sizeof(x));memset(&y,0xa7,sizeof(y));
        a=next(a,x.path);b=original_next(b,y.path);assert(a==b && !memcmp(&x,&y,sizeof(x)));
        assert(x.before==UINT64_C(0xa7a7a7a7a7a7a7a7)&&x.after==x.before);
        if(!a){cases++;return;}
        assert(memchr(x.path,0,sizeof(x.path)) && x.path[0]);paths++;
    }
    assert(!"native enumeration failed to terminate");
}
int main(int argc,char **argv) {
    assert(argc==4 && sizeof(sysdir_search_path_enumeration_state)==4);setbuf(stdout,NULL);
    void *system=dlopen(argv[1],RTLD_LAZY),*native=dlopen(argv[2],RTLD_LAZY);assert(system&&native);
    const char *names[]={"sysdir_start_search_path_enumeration","sysdir_start_search_path_enumeration_private","sysdir_get_next_search_path_enumeration"};
    void *a[3],*b[3];
    for(unsigned i=0;i<3;i++) {
        a[i]=dlsym(system,names[i]);b[i]=dlsym(native,names[i]);assert(a[i]&&b[i]&&a[i]!=b[i]);
        Dl_info owner;assert(dladdr(a[i],&owner)&&!strcmp(owner.dli_fname,argv[3]));
        assert(dladdr(b[i],&owner)&&!strcmp(owner.dli_fname,argv[2]));
    }
    start_fn public_start=(start_fn)a[0],private_start=(start_fn)a[1];next_fn next=(next_fn)a[2];
    for(unsigned dir=0;dir<=101;dir++) {
        if(dir>23 && dir<78)continue;
        for(unsigned mask=0;mask<16;mask++) {
            compare(public_start,next,(start_fn)b[0],(next_fn)b[2],dir,mask);
            compare(private_start,next,(start_fn)b[1],(next_fn)b[2],dir,mask);
        }
        const unsigned extra[]={0x10,0x100,0x400,0x408,0x1000,0x1fff,0xffff};
        for(unsigned i=0;i<7;i++) {
            unsigned mask=extra[i];
            compare(public_start,next,(start_fn)b[0],(next_fn)b[2],dir,mask);
            compare(private_start,next,(start_fn)b[1],(next_fn)b[2],dir,mask);
            if(public_start(dir,mask)!=private_start(dir,mask))private_differences++;
        }
    }
    compare(public_start,next,(start_fn)b[0],(next_fn)b[2],9999,0xffff);
    compare(private_start,next,(start_fn)b[1],(next_fn)b[2],9999,0xffff);
    assert(private_differences && paths);
    unsigned state=public_start(SYSDIR_DIRECTORY_LIBRARY,1);char path[1024];
    assert(next(state,path)&&!strcmp(path,"~/Library"));
    printf("NATIVE_SYSDIR_THREE_PAIRED_ENTRIES_STATE_PATH_ORDER_TERMINATION_BOUNDS_AND_PRIVATE_MASKS_OK %u %u %u\n",cases,paths,private_differences);
}
