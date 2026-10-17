#include <assert.h>
#include <dlfcn.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* swift-6.3.3 Metadata.h: complete request, response and type-name ABI. */
typedef struct { const void *metadata; uintptr_t state; } MetadataResponse;
typedef struct { const char *data; uintptr_t length; } TypeNamePair;
typedef MetadataResponse (__attribute__((swiftcall)) *Accessor)(uintptr_t);
typedef TypeNamePair (__attribute__((swiftcall)) *GetName)(const void *,bool);
typedef const void *(__attribute__((swiftcall)) *GetDescriptor)(const void *);

int main(int argc,char **argv) {
    if (argc<4 || argc%2) return 2;
    void *image=dlopen(argv[1],RTLD_LAZY|RTLD_LOCAL);
    if (!image) { fprintf(stderr,"%s\n",dlerror());return 1; }
    GetName name=(GetName)dlsym(image,"swift_getTypeName");
    GetDescriptor descriptor=(GetDescriptor)dlsym(image,"swift_getTypeContextDescriptor");
    assert(name && descriptor);
    for (int i=2;i<argc;i+=2) {
        char symbol[256];
        assert(strlen(argv[i])+3<sizeof(symbol));
        snprintf(symbol,sizeof(symbol),"%sMa",argv[i]);
        Accessor access=(Accessor)dlsym(image,symbol);assert(access);
        Dl_info owner;assert(dladdr((void *)access,&owner));
        char *actualPath=realpath(owner.dli_fname,NULL),*expectedPath=realpath(argv[1],NULL);
        assert(actualPath && expectedPath && !strcmp(actualPath,expectedPath));
        free(actualPath);free(expectedPath);
        snprintf(symbol,sizeof(symbol),"%sMn",argv[i]);
        const uint32_t *expected=dlsym(image,symbol);assert(expected);
        assert(!(*expected&0x80)); /* Never call a generic accessor without arguments. */
        MetadataResponse first=access(0);assert(first.metadata && first.state==0);
        for (unsigned repeat=0;repeat<16;repeat++) {
            MetadataResponse again=access(0);
            assert(again.metadata==first.metadata && again.state==0);
            assert(descriptor(again.metadata)==expected);
            TypeNamePair text=name(again.metadata,true);
            assert(text.data && text.length==strlen(argv[i+1]));
            assert(!memcmp(text.data,argv[i+1],text.length));
        }
        printf("Original complete type with stable identity: %s\n",argv[i+1]);
    }
    puts("ORIGINAL_SWIFT_COMPLETE_METADATA_DESCRIPTOR_NAME_IDENTITY_OK");
    return 0;
}
