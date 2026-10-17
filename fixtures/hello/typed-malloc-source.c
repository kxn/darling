#include <assert.h>
#include <dlfcn.h>
#include <errno.h>
#include <malloc/malloc.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
typedef unsigned long long type_id;
static void *(*allocate)(size_t,type_id);
static void *(*zero)(size_t,size_t,type_id);
static void (*release)(void*,type_id);
static void *(*resize)(void*,size_t,type_id);
static void *(*pages)(size_t,type_id);
static void *(*aligned)(size_t,size_t,type_id);
static int (*posix)(void**,size_t,size_t,type_id);
static void *(*za)(malloc_zone_t*,size_t,type_id);
static void *(*zc)(malloc_zone_t*,size_t,size_t,type_id);
static void (*zf)(malloc_zone_t*,void*,type_id);
static void *(*zr)(malloc_zone_t*,void*,size_t,type_id);
static void *(*zv)(malloc_zone_t*,size_t,type_id);
static void *(*zm)(malloc_zone_t*,size_t,size_t,type_id);
static void verify(void *ptr,size_t size,unsigned char byte) {
    assert(ptr && malloc_size(ptr)>=size && (uintptr_t)ptr%16==0);
    for(size_t i=0;i<size;i++)assert(((unsigned char *)ptr)[i]==byte);
}
static void *worker(void *argument) {
    type_id id=(uintptr_t)argument;
    for(unsigned i=0;i<64;i++) {
        void *p=allocate(97,id);assert(p);memset(p,(int)id,97);
        p=resize(p,8193,id);verify(p,97,(unsigned char)id);release(p,id);
    }
    return NULL;
}
int main(int argc,char **argv) {
    assert(argc==3);setbuf(stdout,NULL);
    void *image=dlopen(argv[1],RTLD_LAZY);assert(image);
#define LOAD(variable,name) do { *(void **)(&variable)=dlsym(image,"malloc_type_" name);assert(variable);Dl_info owner;assert(dladdr((void *)variable,&owner)&&!strcmp(owner.dli_fname,argv[2])); } while(0)
    LOAD(allocate,"malloc");LOAD(zero,"calloc");LOAD(release,"free");LOAD(resize,"realloc");
    LOAD(pages,"valloc");LOAD(aligned,"aligned_alloc");LOAD(posix,"posix_memalign");
    LOAD(za,"zone_malloc");LOAD(zc,"zone_calloc");LOAD(zf,"zone_free");LOAD(zr,"zone_realloc");LOAD(zv,"zone_valloc");LOAD(zm,"zone_memalign");
    const type_id ids[]={0,0x123456789abcdef0ULL,UINT64_MAX};
    for(unsigned k=0;k<3;k++) {
        type_id id=ids[k];void *p=allocate(97,id);assert(p);memset(p,0xa5,97);verify(p,97,0xa5);
        p=resize(p,8193,id);verify(p,97,0xa5);memset(p,0x5a,8193);
        p=resize(p,33,id);verify(p,33,0x5a);free(p);
        p=malloc(24);assert(p);release(p,id);release(NULL,id);
        p=zero(7,19,id);verify(p,133,0);release(p,id);
        p=pages(73,id);assert(p && (uintptr_t)p%getpagesize()==0);release(p,id);
        for(size_t alignment=16;alignment<=4096;alignment*=4) {
            p=aligned(alignment,alignment*3,id);assert(p && (uintptr_t)p%alignment==0);release(p,id);
            p=NULL;assert(!posix(&p,alignment,137,id)&&p&&(uintptr_t)p%alignment==0);release(p,id);
        }
        p=(void *)1;assert(posix(&p,3,73,id)==EINVAL && p==(void *)1);
        volatile size_t huge=SIZE_MAX;errno=0;assert(!allocate(huge,id)&&errno==ENOMEM);
        errno=0;assert(!zero(huge,2,id)&&errno==ENOMEM);
        p=allocate(32,id);assert(p);memset(p,0x3b,32);errno=0;
        assert(!resize(p,huge,id)&&errno==ENOMEM);verify(p,32,0x3b);release(p,id);
    }
    puts("SOURCE_TYPED_MALLOC_SEVEN_DEFAULT_APIS_REAL_OWNERSHIP_ALIGNMENT_ZEROING_AND_FAILURE_LIFETIME_OK");
    malloc_zone_t *zones[]={malloc_default_zone(),malloc_create_zone(0,0)};assert(zones[0]&&zones[1]&&zones[0]!=zones[1]);
    for(unsigned k=0;k<2;k++) {
        malloc_zone_t *z=zones[k];void *p=za(z,113,ids[k]);assert(p);memset(p,0xb7,113);
        assert(malloc_zone_from_ptr(p)==z || k==0);
        p=zr(z,p,4097,ids[k]);verify(p,113,0xb7);zf(z,p,ids[k]);
        p=zc(z,7,29,ids[k]);verify(p,203,0);zf(z,p,ids[k]);
        p=zv(z,129,ids[k]);assert(p&&(uintptr_t)p%getpagesize()==0);zf(z,p,ids[k]);
        p=zm(z,256,177,ids[k]);assert(p&&(uintptr_t)p%256==0);zf(z,p,ids[k]);
    }
    malloc_destroy_zone(zones[1]);
    puts("SOURCE_TYPED_MALLOC_SIX_ZONE_APIS_DEFAULT_AND_DISTINCT_REAL_ZONE_OK");
    pthread_t threads[4];for(unsigned i=0;i<4;i++)assert(!pthread_create(&threads[i],NULL,worker,(void *)(uintptr_t)(i+1)));
    for(unsigned i=0;i<4;i++)assert(!pthread_join(threads[i],NULL));
    puts("SOURCE_TYPED_MALLOC_ALL_13_UPSTREAM_FALLBACK_APIS_AND_256_THREADED_LIFETIMES_OK");
}
