#include <xpc/xpc.h>
#include <dispatch/dispatch.h>
#include <dlfcn.h>
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef char *(*Reason)(xpc_connection_t);
typedef int (*Requirement)(xpc_connection_t,const char *);
int main(int argc,char **argv) {
    assert(argc==2 || argc==3);
    void *h=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);if(!h){fputs(dlerror(),stderr);return 1;}
    Reason reason=(Reason)dlsym(h,"xpc_connection_copy_invalidation_reason");
    Requirement requirement=(Requirement)dlsym(h,"xpc_connection_set_peer_code_signing_requirement");
    assert(reason && requirement);
    dispatch_queue_t queue=dispatch_queue_create("linuxcode.xpc.connection",NULL);
    for(unsigned i=0;i<32;i++) {
        dispatch_semaphore_t done=dispatch_semaphore_create(0);
        xpc_connection_t connection=xpc_connection_create(NULL,queue);assert(connection);
        if(argc==3) { reason(connection);return 99; }
        assert(reason(connection)==NULL);
        int context=123;xpc_connection_set_context(connection,&context);
        assert(requirement(connection,"anchor apple")==ENOTSUP);
        assert(requirement(connection,"not a valid requirement (")==ENOTSUP);
        assert(xpc_connection_get_context(connection)==&context);
        assert(reason(connection)==NULL);
        xpc_connection_set_event_handler(connection,^(xpc_object_t event) {
            assert(event==XPC_ERROR_CONNECTION_INVALID);
            char *first=reason(connection),*second=reason(connection);
            assert(first && second && first!=second && !strcmp(first,second));
            assert(strstr(first,"cancelled"));first[0]='?';assert(second[0]!='?');
            free(first);free(second);dispatch_semaphore_signal(done);
        });
        xpc_connection_resume(connection);
        xpc_connection_cancel(connection);
        assert(!dispatch_semaphore_wait(done,dispatch_time(DISPATCH_TIME_NOW,5*NSEC_PER_SEC)));
        char *after=reason(connection);assert(after && strstr(after,"cancelled"));free(after);
        xpc_release(connection);dispatch_release(done);
    }
    dispatch_release(queue);
    puts("XPC_32_REAL_CONNECTION_INVALIDATIONS_OWNED_REASONS_AND_UNSUPPORTED_REQUIREMENTS_OK");
    return 0;
}
