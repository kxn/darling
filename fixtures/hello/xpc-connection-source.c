#include <xpc/xpc.h>
#include <dispatch/dispatch.h>
#include <dlfcn.h>
#include <mach-o/loader.h>
#include <pthread.h>
#include <stdatomic.h>
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sched.h>

typedef char* (*Reason)(xpc_connection_t);
typedef int (*Requirement)(xpc_connection_t,const char*);
struct reader {
    xpc_connection_t connection;
    Reason reason;
    dispatch_semaphore_t ready, seen;
    atomic_bool* stop;
    unsigned observations;
};

static void wait_signal(dispatch_semaphore_t semaphore) {
    assert(dispatch_semaphore_wait(semaphore,dispatch_time(DISPATCH_TIME_NOW,5*NSEC_PER_SEC))==0);
}

static void* read_reasons(void* context) {
    struct reader* r=context;
    assert(r->reason(r->connection)==NULL);
    dispatch_semaphore_signal(r->ready);
    bool signalled=false;
    while (!atomic_load_explicit(r->stop,memory_order_acquire)) {
        char* text=r->reason(r->connection);
        if (text) {
            assert(strstr(text,"cancelled"));
            free(text);
            ++r->observations;
            if (!signalled) { signalled=true;dispatch_semaphore_signal(r->seen); }
        }
        sched_yield();
    }
    assert(signalled && r->observations);
    return NULL;
}

static bool has_source_uuid(const char* expected) {
    Dl_info owner;
    assert(dladdr((void*)xpc_connection_cancel,&owner));
    const struct mach_header_64* h=owner.dli_fbase;
    assert(h->magic==MH_MAGIC_64);
    const struct load_command* c=(const void*)(h+1);
    for (unsigned i=0;i<h->ncmds;++i) {
        if (c->cmd==LC_UUID) {
            const struct uuid_command* u=(const void*)c;
            char text[33];
            for (unsigned j=0;j<16;++j) snprintf(text+j*2,3,"%02x",u->uuid[j]);
            return strcmp(text,expected)==0;
        }
        c=(const void*)((const char*)c+c->cmdsize);
    }
    return false;
}

int main(int argc,char** argv) {
    assert(argc==3);
    if (!has_source_uuid(argv[2])) {
        fprintf(stderr,"SOURCE_CONNECTION_BACKEND_UUID_REJECTED\n");return 88;
    }
    void* h=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);
    if (!h) fprintf(stderr,"%s\n",dlerror());
    assert(h);
    Reason reason=dlsym(h,"xpc_connection_copy_invalidation_reason");
    Requirement requirement=dlsym(h,"xpc_connection_set_peer_code_signing_requirement");
    assert(reason && requirement);
    dispatch_queue_t queue=dispatch_queue_create("linuxcode.xpc.source.cancel",NULL);
    dispatch_semaphore_t ready=dispatch_semaphore_create(0),seen=dispatch_semaphore_create(0),done=dispatch_semaphore_create(0);
    xpc_connection_t connection=xpc_connection_create(NULL,queue);assert(connection);
    atomic_bool stop=false;
    struct reader readers[8];pthread_t workers[8];
    // Initialize the adapter's resolver concurrently, before the first query
    // on this process. Each reader must observe both sides of the actual event.
    for (unsigned i=0;i<8;++i) {
        readers[i]=(struct reader){connection,reason,ready,seen,&stop,0};
        assert(pthread_create(&workers[i],NULL,read_reasons,&readers[i])==0);
    }
    for (unsigned i=0;i<8;++i) wait_signal(ready);
    xpc_connection_set_event_handler(connection,^(xpc_object_t event) {
        assert(event==XPC_ERROR_CONNECTION_INVALID);
        char* text=reason(connection);assert(text && strstr(text,"cancelled"));free(text);
        dispatch_semaphore_signal(done);
    });
    xpc_connection_resume(connection);xpc_connection_cancel(connection);
    wait_signal(done);
    for (unsigned i=0;i<8;++i) wait_signal(seen);
    atomic_store_explicit(&stop,true,memory_order_release);
    for (unsigned i=0;i<8;++i) assert(pthread_join(workers[i],NULL)==0);
    xpc_release(connection);dispatch_release(done);dispatch_release(seen);dispatch_release(ready);
    for (unsigned i=0;i<32;++i) {
        dispatch_semaphore_t ended=dispatch_semaphore_create(0);
        xpc_connection_t c=xpc_connection_create(NULL,queue);assert(c && reason(c)==NULL);
        int context=123;xpc_connection_set_context(c,&context);
        assert(requirement(c,"anchor apple")==ENOTSUP);
        assert(requirement(c,"not a valid requirement (")==ENOTSUP);
        assert(xpc_connection_get_context(c)==&context && reason(c)==NULL);
        xpc_connection_set_event_handler(c,^(xpc_object_t event) {
            assert(event==XPC_ERROR_CONNECTION_INVALID);
            char* a=reason(c);char* b=reason(c);
            assert(a && b && a!=b && !strcmp(a,b) && strstr(a,"cancelled"));
            a[0]='?';assert(b[0]!='?');free(a);free(b);
            dispatch_semaphore_signal(ended);
        });
        xpc_connection_resume(c);xpc_connection_cancel(c);wait_signal(ended);
        char* surviving=reason(c);assert(surviving && strstr(surviving,"cancelled"));
        xpc_release(c);
        assert(strstr(surviving,"cancelled"));free(surviving);dispatch_release(ended);
    }
    dispatch_release(queue);
    puts("SOURCE_XPC_8_CONCURRENT_READERS_OBSERVE_REAL_INVALIDATION_AND_32_OWNED_REASON_LIFECYCLES_OK");
    puts("SOURCE_XPC_PEER_SIGNING_REQUIREMENT_RETURNS_UNSUPPORTED_WITHOUT_CONNECTION_MUTATION_OK");
    return 0;
}
