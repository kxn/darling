#include <assert.h>
#include <dlfcn.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
typedef void (*Yield)(void);
static Yield yield;
static void* worker(void* unused) {
    (void)unused;
    for(unsigned i=0;i<128;++i)yield();
    return NULL;
}
int main(int argc,char** argv) {
    assert(argc==2 || argc==3);setbuf(stdout,NULL);
    void* system=dlopen("/usr/lib/libSystem.B.dylib",RTLD_LAZY|RTLD_LOCAL);assert(system);
    yield=(Yield)dlsym(system,"pthread_yield_np");
    if(argc==3) {
        assert(!strcmp(argv[2],"--missing") && !yield);
        puts("BASELINE_LIBSYSTEM_HAS_NO_PTHREAD_YIELD_NP_EXPORT_OK");return 0;
    }
    Dl_info info;assert(yield && dladdr((void*)yield,&info) && !strcmp(info.dli_fname,argv[1]));
    puts("PTHREAD_YIELD_NAMED_REEXPORT_RESOLVES_EXISTING_REAL_HELPER_OK");
    puts("YIELD_BEGIN");
    for(unsigned i=0;i<256;++i)yield();
    puts("YIELD_END");
    pthread_t threads[8];
    for(unsigned i=0;i<8;++i)assert(!pthread_create(&threads[i],NULL,worker,NULL));
    for(unsigned i=0;i<8;++i)assert(!pthread_join(threads[i],NULL));
    puts("PTHREAD_YIELD_REAL_256_MAIN_AND_1024_EIGHT_THREAD_CALLS_OK");
    return 0;
}
