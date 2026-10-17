#include <xpc/xpc.h>
#include <assert.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    void *system=dlopen("/usr/lib/libSystem.B.dylib",RTLD_LAZY|RTLD_LOCAL);assert(system);
    xpc_object_t (*create)(void)=dlsym(system,"xpc_dictionary_create_empty");assert(create);
    xpc_object_t first=create(),second=create();assert(first && second && first!=second);
    assert(xpc_get_type(first)==XPC_TYPE_DICTIONARY && xpc_get_type(second)==XPC_TYPE_DICTIONARY);
    assert(!xpc_dictionary_get_count(first) && !xpc_dictionary_get_count(second));
    char text[]="copied";xpc_dictionary_set_string(first,"text",text);text[0]='X';
    xpc_dictionary_set_int64(first,"number",-123456789);
    const unsigned char payload[]={0,1,2,255};xpc_dictionary_set_data(first,"data",payload,sizeof(payload));
    assert(!strcmp(xpc_dictionary_get_string(first,"text"),"copied"));
    assert(xpc_dictionary_get_int64(first,"number")==-123456789);
    size_t length=0;const void *bytes=xpc_dictionary_get_data(first,"data",&length);
    assert(length==sizeof(payload) && !memcmp(bytes,payload,length));
    assert(xpc_dictionary_get_count(first)==3 && !xpc_dictionary_get_count(second));
    xpc_release(first);xpc_release(second);
    puts("SYSTEM_XPC_EMPTY_REAL_DICTIONARY_MUTATION_COPY_VALUES_INDEPENDENT_INSTANCES_OK");
    return 0;
}
