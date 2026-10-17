#include <assert.h>
#include <dlfcn.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef struct { const void *metadata; uintptr_t state; } MetadataResponse;
typedef struct { const char *data; uintptr_t length; } TypeNamePair;
typedef MetadataResponse (__attribute__((swiftcall)) *Accessor)(uintptr_t);
typedef TypeNamePair (__attribute__((swiftcall)) *GetName)(const void *,bool);
typedef const void *(__attribute__((swiftcall)) *GetDescriptor)(const void *);
typedef void *(*Copy)(void *,const void *,const void *);
typedef void (*Destroy)(void *,const void *);
typedef unsigned (*GetTag)(const void *,const void *);
typedef void (*InjectTag)(void *,unsigned,const void *);
typedef unsigned (*GetSingle)(const void *,unsigned,const void *);
typedef void (*StoreSingle)(void *,unsigned,unsigned,const void *);

int main(int argc,char **argv) {
    if (argc!=2)return 2;
    void *image=dlopen(argv[1],RTLD_LAZY|RTLD_LOCAL);
    if (!image) { fprintf(stderr,"%s\n",dlerror());return 1; }
    Accessor access=(Accessor)dlsym(image,"$s10Foundation3URLV13DirectoryHintOMa");assert(access);
    void *foundation=dlopen("/System/Library/Frameworks/Foundation.framework/Versions/C/Foundation",RTLD_LAZY|RTLD_LOCAL);
    assert(foundation && dlsym(foundation,"$s10Foundation3URLV13DirectoryHintOMa")==access);
    const uint32_t *literal=dlsym(foundation,"$s10Foundation3URLV13DirectoryHintO13inferFromPathyA2EmFWC");
    assert(literal && *literal==3);
    const uint32_t *desc=dlsym(image,"$s10Foundation3URLV13DirectoryHintOMn");assert(desc);
    MetadataResponse first=access(0),again=access(0);
    assert(first.state==0 && again.state==0 && first.metadata==again.metadata);
    GetDescriptor descriptor=(GetDescriptor)dlsym(image,"swift_getTypeContextDescriptor");assert(descriptor);
    assert(descriptor(first.metadata)==desc);
    GetName name=(GetName)dlsym(image,"swift_getTypeName");assert(name);
    TypeNamePair text=name(first.metadata,true);
    const char *expected="Foundation.URL.DirectoryHint";
    assert(text.length==strlen(expected) && !memcmp(text.data,expected,text.length));
    const void **vwt=((const void ***)first.metadata)[-1];
    const uintptr_t *layout=(const uintptr_t *)(vwt+8);assert(layout[0]==1 && layout[1]==1);
    for (unsigned index=0;index<4;index++) {
        unsigned char value[3]={0xa5,0xff,0x5a};
        ((InjectTag)vwt[13])(value+1,index,first.metadata);
        assert(value[0]==0xa5 && value[1]==index && value[2]==0x5a);
        assert(((GetTag)vwt[11])(value+1,first.metadata)==index);
        unsigned char copy[3]={0xa5,0xff,0x5a};
        assert(((Copy)vwt[2])(copy+1,value+1,first.metadata)==copy+1);
        assert(copy[0]==0xa5 && copy[1]==index && copy[2]==0x5a);
        ((Destroy)vwt[1])(copy+1,first.metadata);
    }
    unsigned counts[]={0,1,2,252,253,254,65535,16777212};unsigned trials=0;
    for (unsigned i=0;i<sizeof(counts)/sizeof(counts[0]);i++) {
        unsigned count=counts[i],tags[]={0,count,count?1:0,count<252?count:252,count<253?count:253};
        for (unsigned j=0;j<sizeof(tags)/sizeof(tags[0]);j++) {
            unsigned char storage[8];memset(storage,0xa5,sizeof(storage));storage[1]=3;
            ((StoreSingle)vwt[7])(storage+1,tags[j],count,first.metadata);
            assert(((GetSingle)vwt[6])(storage+1,count,first.metadata)==tags[j]);
            assert(storage[0]==0xa5 && storage[6]==0xa5 && storage[7]==0xa5);trials++;
        }
    }
    printf("ORIGINAL_DIRECTORY_HINT_METADATA_REFLECTION_CASES_COPY_AND_SINGLE_PAYLOAD_ROUNDTRIPS_OK %u\n",trials);
    return 0;
}
