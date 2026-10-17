#include <xpc/xpc.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <dlfcn.h>
#include <stdint.h>
#include <stdlib.h>
int main(void) {
    void *(*typed_malloc)(size_t,uint64_t) = dlsym(RTLD_DEFAULT,"malloc_type_malloc");
    void *(*typed_realloc)(void *,size_t,uint64_t) = dlsym(RTLD_DEFAULT,"malloc_type_realloc");
    void *(*typed_calloc)(size_t,size_t,uint64_t) = dlsym(RTLD_DEFAULT,"malloc_type_calloc");
    assert(typed_malloc && typed_realloc && typed_calloc);
    unsigned char *bytes=typed_malloc(32,0);
    assert(bytes);
    for (int i=0;i<32;i++) bytes[i]=(unsigned char)(i+1);
    bytes=typed_realloc(bytes,96,0);
    assert(bytes);
    for (int i=0;i<32;i++) assert(bytes[i]==(unsigned char)(i+1));
    memset(bytes+32,0x5a,64);
    free(bytes);
    bytes=typed_calloc(8,16,0);
    assert(bytes);
    for (int i=0;i<128;i++) assert(bytes[i]==0);
    free(bytes);
    assert(typed_calloc(SIZE_MAX,16,0)==NULL);
    puts("TYPED_CALLOC_ZEROES_AND_REJECTS_OVERFLOW_OK");
    xpc_object_t object = xpc_dictionary_create_empty();
    assert(object && xpc_get_type(object) == XPC_TYPE_DICTIONARY);
    assert(xpc_dictionary_get_count(object) == 0);
    xpc_dictionary_set_string(object, "message", "Darling actual XPC");
    xpc_dictionary_set_int64(object, "counter", 42);
    assert(xpc_dictionary_get_count(object) == 2);
    assert(strcmp(xpc_dictionary_get_string(object, "message"), "Darling actual XPC") == 0);
    assert(xpc_dictionary_get_int64(object, "counter") == 42);
    xpc_release(object);
    puts("MODERN_XPC_DICTIONARY_ROUNDTRIP_OK");
    puts("TYPED_ALLOCATION_REALLOC_PRESERVES_BYTES_OK");
}
