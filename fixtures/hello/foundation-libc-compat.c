#include <sys/types.h>
#include <malloc/malloc.h>
#include <crt_externs.h>
#include <dlfcn.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <errno.h>
#include <unistd.h>
typedef void (*Void)(void);
typedef int (*Receipt)(void);
typedef void *(*ZoneMalloc)(malloc_zone_t *,size_t,uint64_t);
typedef void *(*ZoneCalloc)(malloc_zone_t *,size_t,size_t,uint64_t);
typedef void *(*ZoneRealloc)(malloc_zone_t *,void *,size_t,uint64_t);
static Void environmentLock,environmentUnlock;
static pthread_mutex_t control=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t condition=PTHREAD_COND_INITIALIZER;
static bool go=false;
static _Atomic bool started=false,finished=false;
static void *blocked_setter(void *unused) {
    pthread_mutex_lock(&control);while (!go)pthread_cond_wait(&condition,&control);pthread_mutex_unlock(&control);
    atomic_store(&started,true);assert(!setenv("LINUXCODE_ENV_LOCK_TEST","changed",1));atomic_store(&finished,true);return NULL;
}
static const char *raw_value(const char *key) {
    size_t length=strlen(key);
    for (char **entry=*_NSGetEnviron();entry && *entry;entry++)
        if (!strncmp(*entry,key,length) && (*entry)[length]=='=')return *entry+length+1;
    return NULL;
}
static void *stress_setter(void *argument) {
    unsigned id=(unsigned)(uintptr_t)argument;
    char key[64];snprintf(key,sizeof(key),"LINUXCODE_ENV_STRESS_%u",id);
    for (unsigned i=0;i<1000;i++) {
        char value[64];snprintf(value,sizeof(value),"worker_%u_value_%u",id,i);
        assert(!setenv(key,value,1));
        environmentLock();const char *actual=raw_value(key);assert(actual && !strcmp(actual,value));environmentUnlock();
    }
    assert(!unsetenv(key));return NULL;
}
static void exit_first(void) { puts("FOUNDATION_LIBC_EXIT_FIRST"); }
static void exit_second(void) { puts("FOUNDATION_LIBC_EXIT_SECOND"); }
extern int csops(pid_t,unsigned int,void *,size_t);
int main(int argc,char **argv) {
    assert(argc==2 || argc==3);
    void *library=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);
    if (!library) { fprintf(stderr,"%s\n",dlerror());return 1; }
    environmentLock=(Void)dlsym(library,"environ_lock_np");environmentUnlock=(Void)dlsym(library,"environ_unlock_np");
    Receipt receipt=(Receipt)dlsym(library,"_atexit_receipt");
    ZoneMalloc allocate=(ZoneMalloc)dlsym(library,"malloc_type_zone_malloc");
    ZoneCalloc zero=(ZoneCalloc)dlsym(library,"malloc_type_zone_calloc");
    ZoneRealloc resize=(ZoneRealloc)dlsym(library,"malloc_type_zone_realloc");
    Void yield=(Void)dlsym(library,"pthread_yield_np");
    assert(environmentLock && environmentUnlock && receipt && allocate && zero && resize && yield);
    if (argc==3) { environmentLock();return 99; }
    Dl_info owner;assert(dladdr((void *)environmentLock,&owner));
    char *actual=realpath(owner.dli_fname,NULL),*expected=realpath(argv[1],NULL);
    assert(actual && expected && !strcmp(actual,expected));free(actual);free(expected);
    assert(!setenv("LINUXCODE_ENV_LOCK_TEST","initial",1));
    pthread_t setter;assert(!pthread_create(&setter,NULL,blocked_setter,NULL));
    environmentLock();pthread_mutex_lock(&control);go=true;pthread_cond_signal(&condition);pthread_mutex_unlock(&control);
    while (!atomic_load(&started))usleep(1000);
    usleep(100000);assert(!atomic_load(&finished));
    assert(!strcmp(raw_value("LINUXCODE_ENV_LOCK_TEST"),"initial"));environmentUnlock();
    assert(!pthread_join(setter,NULL) && atomic_load(&finished));
    assert(!strcmp(getenv("LINUXCODE_ENV_LOCK_TEST"),"changed"));assert(!unsetenv("LINUXCODE_ENV_LOCK_TEST"));
    pthread_t workers[4];
    for (unsigned i=0;i<4;i++)assert(!pthread_create(&workers[i],NULL,stress_setter,(void *)(uintptr_t)i));
    for (unsigned i=0;i<4;i++)assert(!pthread_join(workers[i],NULL));
    const size_t sizes[]={0,1,15,31,4097,65536};const uint64_t types[]={0,1,UINT64_MAX};
    malloc_zone_t *zone=malloc_default_zone();assert(zone);
    for (unsigned s=0;s<6;s++)for (unsigned t=0;t<3;t++) {
        size_t size=sizes[s];unsigned char *pointer=allocate(zone,size,types[t]);assert(pointer || !size);
        if (size)memset(pointer,0xa9,size);
        unsigned char *grown=resize(zone,pointer,size+17,types[t]);assert(grown);
        for (size_t i=0;i<size;i++)assert(grown[i]==0xa9);malloc_zone_free(zone,grown);
        unsigned char *zeros=zero(zone,7,size+1,types[t]);assert(zeros);
        for (size_t i=0;i<7*(size+1);i++)assert(!zeros[i]);malloc_zone_free(zone,zeros);
    }
    assert(!zero(zone,SIZE_MAX,2,0));
    uint32_t category=UINT32_MAX;errno=0;
    assert(csops(0,17,&category,sizeof(category))==-1 && errno==ENOSYS && category==UINT32_MAX);
    assert(!atexit(exit_first));for (unsigned i=0;i<16;i++)assert(receipt()==0);assert(!atexit(exit_second));
    yield();
    puts("FOUNDATION_LIBC_REAL_ENV_LOCK_THREADS_ZONE_ALLOCATIONS_AND_RECEIPT_QUERY_OK");
    return 0;
}
