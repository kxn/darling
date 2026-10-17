#include <objc/runtime.h>
#include <dlfcn.h>
#include <pthread.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
typedef SEL (*Lookup)(const char *);
static Lookup lookup;
static void *worker(void *argument) {
    unsigned id=(unsigned)(uintptr_t)argument;
    for (unsigned i=0;i<3000;i++) {
        char name[96];snprintf(name,sizeof(name),"linuxcode_selector_worker_%u_%u:",id,i);
        assert(!lookup(name));
        SEL actual=sel_registerName(name);assert(actual);
        char *copy=strdup(name);assert(copy);
        assert(lookup(copy)==actual);memset(copy,'!',strlen(copy));free(copy);
        assert(lookup(name)==actual && !strcmp(sel_getName(actual),name));
    }
    return NULL;
}
int main(int argc,char **argv) {
    assert(argc==2);
    void *library=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);
    if (!library) { fprintf(stderr,"%s\n",dlerror());return 1; }
    lookup=(Lookup)dlsym(library,"sel_lookUpByName");assert(lookup);
    assert(lookup("class")==sel_registerName("class"));
    assert(!lookup(NULL));
    const char *names[]={"","中文方法:","linuxcode_nonascii_é:","linuxcode_caseSensitive:","LINUXCODE_CASESENSITIVE:","a:b:c:d:e:f:g:"};
    for (unsigned i=0;i<sizeof(names)/sizeof(*names);i++) {
        for (unsigned repeat=0;repeat<4;repeat++)assert(!lookup(names[i]));
        SEL actual=sel_registerName(names[i]);assert(actual && lookup(names[i])==actual);
        char *copy=strdup(names[i]);assert(lookup(copy)==actual);free(copy);
    }
    pthread_t threads[4];
    for (unsigned i=0;i<4;i++)assert(!pthread_create(&threads[i],NULL,worker,(void *)(uintptr_t)i));
    for (unsigned i=0;i<4;i++)assert(!pthread_join(threads[i],NULL));
    for (unsigned i=0;i<4;i++)for (unsigned j=0;j<3000;j++) {
        char name[96];snprintf(name,sizeof(name),"linuxcode_selector_worker_%u_%u:",i,j);
        SEL actual=lookup(name);assert(actual && actual==sel_registerName(name));
    }
    for (unsigned i=0;i<64;i++) {
        char name[96];snprintf(name,sizeof(name),"linuxcode_selector_never_registered_%u:",i);
        assert(!lookup(name) && !lookup(name));
    }
    puts("OBJC_SELECTOR_EXISTING_IDENTITY_UNKNOWN_NO_REGISTRATION_UTF8_AND_CONCURRENT_GROWTH_OK");
    return 0;
}
