// Private C ABI checked against the pinned 25G83 implementation: capacity in
// edi; add receives dimensions/key/value in rdi/rsi/rdx and returns a Boolean.
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <dlfcn.h>
#include <objc/runtime.h>
#include <stdio.h>
#include <string.h>
extern void os_release(void *);

int main(int argc,char **argv) {
    if(argc!=2)return 2;
    void *library=dlopen(argv[1],RTLD_LAZY|RTLD_LOCAL);
    if(!library){fprintf(stderr,"%s\n",dlerror());return 1;}
    void *(*create)(uint8_t)=dlsym(library,"os_metric_dimensions_create");
    bool (*add)(void *,const char *,const char *)=dlsym(library,"os_metric_dimensions_add");
    assert(create && add);
    void *first=create(2),*second=create(1);
    assert(first && second && first!=second);
    assert(strcmp(object_getClassName((id)first),"OS_os_metric_dimensions")==0);
    assert(add(first,"platform","linux"));
    assert(add(first,"runtime","darling"));
    assert(!add(first,"excess","rejected"));
    assert(add(second,"independent","object"));
    assert(!add(second,"excess","rejected"));
    os_release(first);os_release(second);
    puts("NATIVE_METRIC_DIMENSIONS_ADD_CAPACITY_REJECT_LIFECYCLE_OK");
}
