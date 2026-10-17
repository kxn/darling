#import <Foundation/Foundation.h>
#include <os/log_private.h>
#include <sys/mman.h>
#include <dlfcn.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "native-compose-oracle.h"
static unsigned checks,calls,descriptions;
#define CHECK(c) do {checks++;if(!(c)){fprintf(stderr,"COMPOSE_FAIL line=%d %s\n",__LINE__,#c);abort();}}while(0)
struct blob {char* bytes;uint32_t used,capacity;uint64_t maximum;};
static struct {os_log_pack_t pack;os_log_t log;uint8_t type;uint32_t flags;const uint8_t* encoded;uint32_t size;char* initial;uint32_t capacity;uint64_t maximum;unsigned composed;} captured;
static char oracle_text[]="oracle-callee";
static const char* oracle_format;
static const void* oracle_dso;
static void flatten_spy(os_log_pack_t pack,os_log_t log,uint8_t type,uint32_t flags,const uint8_t* encoded,uint32_t size,struct blob* result) {
    CHECK(pack->olp_format==oracle_format && pack->olp_mh==oracle_dso && pack->olp_pc);
    captured.log=log;captured.type=type;captured.flags=flags;captured.encoded=encoded;captured.size=size;
    captured.composed=result!=NULL;
    if(result){captured.initial=result->bytes;captured.capacity=result->capacity;captured.maximum=result->maximum;CHECK(result->used==0);result->bytes=oracle_text;}
}
static void shortage(void) {abort();}
static void* oracle(void) {
    unsigned char* code=mmap(NULL,4096,PROT_READ|PROT_WRITE,MAP_ANON|MAP_PRIVATE,-1,0);CHECK(code!=MAP_FAILED);
    memcpy(code,native_compose_code,sizeof native_compose_code);
    const void* targets[]={__error,flatten_spy,strdup,shortage};
    for(unsigned i=0;i<4;i++) {
        unsigned char* stub=code+512+16*i;stub[0]=0xff;stub[1]=0x25;memset(stub+2,0,4);memcpy(stub+6,&targets[i],8);
        int32_t delta=(int32_t)((stub)-(code+native_call_sites[i]+5));memcpy(code+native_call_sites[i]+1,&delta,4);
    }
    code[600]=0;int32_t displacement=(int32_t)(600-native_empty_next);memcpy(code+native_empty_displacement,&displacement,4);
    CHECK(mprotect(code,4096,PROT_READ|PROT_EXEC)==0);return code;
}
@interface CountedDescription:NSObject @end
@implementation CountedDescription
- (NSString*)description {descriptions++;return @"object-value";}
@end
#define CASE(TEXT,MODE,CAP,FORMAT,...) do { \
    const size_t length=__builtin_os_log_format_buffer_size(FORMAT,##__VA_ARGS__); \
    uint8_t encoded[length];__builtin_os_log_format(encoded,FORMAT,##__VA_ARGS__); \
    char guarded[260];memset(guarded,0x5a,sizeof guarded);char* buffer=(CAP)<0?NULL:guarded+2; \
    const char* output=NULL;const char* original_format=FORMAT;unsigned old=calls;errno=ENOENT; \
    char* text=_os_log_send_and_compose_impl(MODE,&output,buffer,(CAP)<0?0:(CAP),(void*)main,log,OS_LOG_TYPE_DEFAULT,FORMAT,encoded,length); \
    CHECK(errno==ENOENT);CHECK(output==original_format);CHECK(calls==old+!!((MODE)&1)); \
    if((MODE)&2){CHECK(text && !strcmp(text,TEXT));if(buffer && strlen(TEXT)<(unsigned)(CAP))CHECK(text==buffer);else CHECK(text!=buffer);if(text!=buffer)free(text);} \
    else CHECK(text==NULL); \
    CHECK(guarded[0]==0x5a && guarded[1]==0x5a && guarded[258]==0x5a && guarded[259]==0x5a); \
}while(0)
int main(void) {@autoreleasepool{
    typedef char*(*native_fn)(unsigned,const char**,char*,uint32_t,void*,os_log_t,uint8_t,const char*,uint8_t*,uint32_t);
    native_fn native=oracle();unsigned char fake_log[128]={0},encoded[]={0,0};
    oracle_format="native ABI";oracle_dso=(void*)main;
    const uint8_t types[]={0,1,2,16,17,0x90};
    unsigned oracle_cases=0;
    for(unsigned mode=0;mode<8;mode++)for(unsigned t=0;t<6;t++)for(unsigned privacy=0;privacy<2;privacy++)for(unsigned provided=0;provided<2;provided++) {
        memset(&captured,0,sizeof captured);fake_log[61]=privacy?2:0;char scratch[17];const char* out=NULL;
        errno=EBUSY;char* result=native(mode,&out,provided?scratch:NULL,provided?17:0,(void*)oracle_dso,(os_log_t)fake_log,types[t],oracle_format,encoded,sizeof encoded);
        CHECK(out==oracle_format);CHECK(captured.log==(os_log_t)fake_log);CHECK(captured.type==types[t]);CHECK(captured.encoded==encoded && captured.size==2);
        uint32_t flags=EBUSY|((mode&1)?0:0x1000000)|((mode&2)?0x8000000:0)|((types[t]&0x7f)==17?0x100000:0)|((privacy && (types[t]&0x7e)==16)?0x800000:0);
        CHECK(captured.flags==flags);CHECK(captured.composed==!!(mode&2));
        if(mode&2){CHECK(result==oracle_text);CHECK(captured.initial!=NULL);CHECK(captured.capacity==(provided?17:1));CHECK(captured.maximum==0x100000);if(provided)CHECK(captured.initial==scratch);}
        else CHECK(result==NULL);
        oracle_cases++;
    }
    CHECK(munmap((void*)native,4096)==0);
    Dl_info owner={0};CHECK(dladdr((void*)_os_log_send_and_compose_impl,&owner));CHECK(strstr(owner.dli_fname,"/runtime/log-compose-runtime/libraries/libTrace.dylib"));
    os_log_t log=os_log_create("org.darling.compose","real-source");CHECK(log);
    // With no hook installed, sending and composing share the one decode.
    // Existing hook serialization separately materializes object descriptions.
    CountedDescription* object=[CountedDescription new];descriptions=0;
    uint8_t object_bytes[__builtin_os_log_format_buffer_size("%{public}@",object)];
    __builtin_os_log_format(object_bytes,"%{public}@",object);char object_buffer[256];
    CHECK(_os_log_send_and_compose_impl(3,NULL,object_buffer,sizeof object_buffer,(void*)main,log,0,"%{public}@",object_bytes,sizeof object_bytes)==object_buffer);
    CHECK(!strcmp(object_buffer,"object-value") && descriptions==1);[object release];
    os_log_set_hook(OS_LOG_TYPE_DEBUG,^(os_log_type_t type,os_log_message_t message){CHECK(type==os_log_get_type(message));calls++;});
    for(unsigned mode=0;mode<8;mode++) {
        CASE("literal 100%",mode,256,"literal 100%%");
        CASE("integer=-77",mode,256,"integer=%{public}d",-77);
        CASE("value=hello",mode,3,"value=%{public}s","hello");
        CASE("你好 Linux",mode,-1,"%{public}@",@"你好 Linux");
        CASE("<private>",mode,256,"%{private}s","must-not-appear");
        CASE("No such file or directory",mode,0,"%m");
    }
    CASE("exact",3,6,"exact");CASE("heap",2,4,"heap");CASE("",2,1,"");CASE("",2,-1,"");
    const size_t size=os_log_pack_size("saved %m");unsigned char storage[size];os_log_pack_t pack=(os_log_pack_t)storage;
    errno=ERANGE;os_log_pack_fill(pack,size,ENOENT,"saved %m");CHECK(errno==ERANGE);
    char small[2];unsigned old=calls;char* text=os_log_pack_send_and_compose(pack,log,OS_LOG_TYPE_ERROR,small,sizeof small);
    CHECK(text && text!=small && !strcmp(text,"saved No such file or directory"));CHECK(errno==ERANGE && calls==old+1);free(text);
    uint8_t invalid[]={0,1};errno=EDOM;
    CHECK(_os_log_send_and_compose_impl(2,NULL,NULL,0,(void*)main,log,0,"%d",invalid,sizeof invalid)==NULL);CHECK(errno==EDOM);
    printf("SOURCE_LOG_SEND_COMPOSE_REAL_FORMAT_OWNERSHIP_DELIVERY_OK checks=%u oracle_wrapper_cases=%u sends=%u\n",checks,oracle_cases,calls);
    return 0;
}}
