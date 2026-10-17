#include <assert.h>
#include <dlfcn.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/* swift-6.3.3 ABI/Metadata.h and Runtime/HeapObject.h, x86_64. */
typedef struct { const void *metadata; uintptr_t state; } MetadataResponse;
typedef struct { const char *data; uintptr_t length; } TypeNamePair;
typedef MetadataResponse (__attribute__((swiftcall)) *Accessor)(uintptr_t);
typedef TypeNamePair (__attribute__((swiftcall)) *GetName)(const void *, bool);
typedef const void *(__attribute__((swiftcall)) *GetDescriptor)(const void *);

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    void *image=dlopen(argv[1],RTLD_LAZY|RTLD_LOCAL);
    if (!image) { fprintf(stderr,"%s\n",dlerror()); return 1; }
    GetName name=(GetName)dlsym(image,"swift_getTypeName");
    GetDescriptor descriptor=(GetDescriptor)dlsym(image,"swift_getTypeContextDescriptor");
    assert(name && descriptor);
    const char *types[]={
        "$s19CollectionsInternal10_HashTableV6HeaderV",
        "$s19CollectionsInternal10_DequeSlotV",
        "$s19CollectionsInternal10_HashTableV7StorageC"
    };
    for (unsigned index=0;index<sizeof(types)/sizeof(types[0]);++index) {
        char symbol[256];
        snprintf(symbol,sizeof(symbol),"%sMa",types[index]);
        Accessor access=(Accessor)dlsym(image,symbol);assert(access);
        snprintf(symbol,sizeof(symbol),"%sMn",types[index]);
        const void *expected=dlsym(image,symbol);assert(expected);
        MetadataResponse first=access(0),second=access(0);
        assert(first.metadata && first.state==0 && second.metadata==first.metadata && second.state==0);
        assert(descriptor(first.metadata)==expected);
        TypeNamePair text=name(first.metadata,true);
        assert(text.data && text.length>20 && text.length<512);
        assert(!memcmp(text.data,"CollectionsInternal.",20));
        printf("Original type: %.*s\n",(int)text.length,text.data);
    }
    puts("ORIGINAL_COLLECTIONS_STRUCT_AND_RESILIENT_CLASS_METADATA_REFLECTION_CACHE_OK");
    return 0;
}
