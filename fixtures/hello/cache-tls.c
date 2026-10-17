#include <assert.h>
#include <dlfcn.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct Descriptor { void *(*thunk)(void *); uintptr_t key, offset; };
static struct Descriptor *descriptor;
static pthread_mutex_t mutex=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t condition=PTHREAD_COND_INITIALIZER;
static unsigned arrived, generation;
static void *addresses[3];

static void rendezvous(void) {
    pthread_mutex_lock(&mutex);
    unsigned before=generation;
    if (++arrived==3) { arrived=0; ++generation; pthread_cond_broadcast(&condition); }
    else while (generation==before) pthread_cond_wait(&condition,&mutex);
    pthread_mutex_unlock(&mutex);
}
static void *worker(void *argument) {
    uintptr_t index=(uintptr_t)argument;
    uint64_t *storage=descriptor->thunk(descriptor);
    assert(storage && *storage==0);
    addresses[index]=storage;
    uint64_t pattern=UINT64_C(0x1122334455667700)+index;
    *storage=pattern;
    rendezvous();
    assert(addresses[0]!=addresses[1] && addresses[1]!=addresses[2] && addresses[0]!=addresses[2]);
    assert(descriptor->thunk(descriptor)==storage && *storage==pattern);
    rendezvous();
    *storage=0;
    return NULL;
}
int main(int argc,char **argv) {
    if (argc!=4) return 2;
    void *image=dlopen(argv[1],RTLD_LAZY|RTLD_LOCAL);
    if (!image) { fprintf(stderr,"%s\n",dlerror());return 1; }
    void *anchor=dlsym(image,argv[2]);
    Dl_info info;
    assert(anchor && dladdr(anchor,&info) && info.dli_fbase);
    assert(*(uint32_t *)info.dli_fbase==UINT32_C(0xfeedfacf));
    descriptor=(void *)((char *)info.dli_fbase+strtoull(argv[3],NULL,0));
    assert(descriptor->thunk && descriptor->key && descriptor->offset==0);
    pthread_t threads[2];
    for (uintptr_t i=0;i<2;++i) assert(pthread_create(&threads[i],NULL,worker,(void *)i)==0);
    worker((void *)2);
    for (unsigned i=0;i<2;++i) assert(pthread_join(threads[i],NULL)==0);
    assert(*(uint64_t *)descriptor->thunk(descriptor)==0);
    puts("ORIGINAL_CACHE_TLV_THUNK_MAIN_AND_TWO_THREADS_ISOLATED_OK");
}
