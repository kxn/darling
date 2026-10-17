#import <Foundation/Foundation.h>
#include <os/log_private.h>
#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include "native-pack-oracle.h"

static unsigned checks,calls,faults;
static const char *expected;
static const void *expected_pc;
#define CHECK(c) do { checks++; if(!(c)){fprintf(stderr,"LOG_PACK_FAIL %d %s\n",__LINE__,#c);abort();} } while(0)
static void *executable(const void *bytes,size_t length){
    void *code=mmap(NULL,4096,PROT_READ|PROT_WRITE,MAP_ANON|MAP_PRIVATE,-1,0);
    CHECK(code!=MAP_FAILED);memcpy(code,bytes,length);
    CHECK(mprotect(code,4096,PROT_READ|PROT_EXEC)==0);return code;
}
static void fault(const struct os_log_fault_info_s *info){
    CHECK(info->pc==expected_pc);CHECK(!strcmp(info->message,"fault 42"));faults++;
}
#define PACK_CASE(TEXT,TYPE,FORMAT,...) do { \
    const size_t size=os_log_pack_size(FORMAT,##__VA_ARGS__); \
    unsigned char storage[size+16];memset(storage,0xa5,sizeof(storage)); \
    os_log_pack_t pack=(os_log_pack_t)(storage+8); \
    errno=EBUSY;os_log_pack_fill(pack,size,ENOENT,FORMAT,##__VA_ARGS__);CHECK(errno==EBUSY); \
    expected=TEXT;expected_pc=pack->olp_pc;unsigned old=calls; \
    errno=ERANGE;os_log_pack_send(pack,log,TYPE);CHECK(errno==ERANGE);CHECK(calls==old+1); \
    for(unsigned i=0;i<8;i++){CHECK(storage[i]==0xa5);CHECK(storage[size+8+i]==0xa5);} \
} while(0)
int main(void){@autoreleasepool{
    const void *entries[]={(void*)_os_log_pack_size,(void*)_os_log_pack_fill,(void*)os_log_pack_send};
    for(unsigned i=0;i<3;i++){Dl_info image;CHECK(dladdr(entries[i],&image));CHECK(strstr(image.dli_fname,"/runtime/libtrace-pack-source/libraries/libTrace.dylib"));}
    size_t (*native_size)(size_t)=executable(native_pack_size,sizeof(native_pack_size));
    uint8_t *(*native_fill)(os_log_pack_t,size_t,int,const void*,const char*)=executable(native_pack_fill,sizeof(native_pack_fill));
    CHECK(sizeof(struct os_log_pack_s)==72);CHECK(offsetof(struct os_log_pack_s,olp_data)==68);
    const size_t sizes[]={0,2,18,22,128,512,4096,65463};
    for(unsigned n=0;n<sizeof(sizes)/sizeof(sizes[0]);n++){
        size_t size=_os_log_pack_size(sizes[n]);CHECK(size==native_size(sizes[n]));
        unsigned char *ours=malloc(size+32),*original=malloc(size+32);CHECK(ours&&original);
        memset(ours,0xa5,size+32);memset(original,0xa5,size+32);
        os_log_pack_t a=(os_log_pack_t)(ours+16),b=(os_log_pack_t)(original+16);
        errno=EBUSY;uint8_t *x=_os_log_pack_fill(a,size,ENOENT,(void*)main,"oracle");CHECK(errno==EBUSY);
        uint8_t *y=native_fill(b,size,ENOENT,(void*)main,"oracle");CHECK(errno==EBUSY);
        CHECK(x-ours==y-original);CHECK(a->olp_pc&&b->olp_pc);
        /* The two genuine call sites differ; every other written byte and
         * untouched guard/payload byte must match the original Intel code. */
        a->olp_pc=b->olp_pc;CHECK(memcmp(ours,original,size+32)==0);
        free(ours);free(original);
    }
    CHECK(munmap((void*)native_size,4096)==0);CHECK(munmap((void*)native_fill,4096)==0);
    void *provider=dlopen("/usr/lib/libDarlingMetrics.dylib",RTLD_LAZY|RTLD_LOCAL);CHECK(provider);
    char *(*copy_message)(os_log_message_t)=dlsym(provider,"os_log_copy_message_string");CHECK(copy_message);
    os_log_t log=os_log_create("org.darling.log-pack","actual-packs");CHECK(log);
    os_log_set_hook(OS_LOG_TYPE_DEBUG,^(os_log_type_t type,os_log_message_t message){
        CHECK(os_log_get_type(message)==type);CHECK(!strcmp(message->subsystem,"org.darling.log-pack"));
        CHECK(!strcmp(message->category,"actual-packs"));CHECK(!message->privdata&&!message->privdata_sz);
        char *text=copy_message(message);CHECK(text&&expected&&!strcmp(text,expected));
        printf("LOG_PACK_TEXT %s\n",text);free(text);calls++;
    });
    os_log_set_fault_callback(fault);
    PACK_CASE("literal 100%",OS_LOG_TYPE_DEFAULT,"literal 100%%");
    PACK_CASE("integer=-77",OS_LOG_TYPE_INFO,"integer=%{public}d",-77);
    PACK_CASE("hello 42",OS_LOG_TYPE_ERROR,"%{public}s %{public}d","hello",42);
    PACK_CASE("你好 Linux",OS_LOG_TYPE_DEBUG,"%{public}@",@"你好 Linux");
    PACK_CASE("<private>",OS_LOG_TYPE_ERROR,"%{private}s","must-not-appear");
    PACK_CASE("No such file or directory",OS_LOG_TYPE_ERROR,"%m");
    PACK_CASE("1.25",OS_LOG_TYPE_DEFAULT,"%{public}.2f",1.25);
    PACK_CASE("fault 42",OS_LOG_TYPE_FAULT,"fault %{public}d",42);CHECK(faults==1);
    CHECK(calls==8);printf("SOURCE_LOG_PACK_NATIVE_LEAF_ABI_AND_ACTUAL_DELIVERY_OK checks=%u calls=%u\n",checks,calls);
    return 0;
}}
