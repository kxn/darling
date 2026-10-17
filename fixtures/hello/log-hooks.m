#import <Foundation/Foundation.h>
#include <os/log_private.h>
#include <Block.h>
#include <dlfcn.h>
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
static unsigned checks,calls,destructions,faults;
static const char *expected;
static os_log_t test_log;
static char *(*copy_message)(os_log_message_t);
#ifndef EXPECTED_LIBTRACE_PATH
#define EXPECTED_LIBTRACE_PATH "/runtime/libtrace-hooks-source/"
#endif
#define CHECK(c) do{__sync_fetch_and_add(&checks,1);if(!(c)){fprintf(stderr,"LOG_HOOK_FAIL line=%d %s\n",__LINE__,#c);abort();}}while(0)
#define EMIT(TYPE,FORMAT,...) do{unsigned size=__builtin_os_log_format_buffer_size(FORMAT,##__VA_ARGS__);uint8_t bytes[size];__builtin_os_log_format(bytes,FORMAT,##__VA_ARGS__);int saved_error=errno;_os_log_impl(NULL,test_log,TYPE,FORMAT,bytes,size);CHECK(errno==saved_error);}while(0)
#define CASE(EXPECTED,FORMAT,...) do{expected=EXPECTED;unsigned old=calls;EMIT(OS_LOG_TYPE_ERROR,FORMAT,##__VA_ARGS__);CHECK(calls==old+1);}while(0)
@interface HookOwner:NSObject
-(unsigned)identity;
@end
@implementation HookOwner
-(unsigned)identity{return 42;}
-(void)dealloc{__sync_fetch_and_add(&destructions,1);[super dealloc];}
@end
static void fault(const struct os_log_fault_info_s *info){
 CHECK(info->version==1&&info->log==test_log);CHECK(!strcmp(info->subsystem,"org.darling.log-hook"));CHECK(!strcmp(info->category,"actual-events"));CHECK(!strcmp(info->format,"fault %{public}d"));CHECK(!strcmp(info->message,"fault 42"));Dl_info image;CHECK(info->pc&&dladdr(info->pc,&image));__sync_fetch_and_add(&faults,1);
}
static void *worker(void *arg){@autoreleasepool{for(unsigned i=0;i<50;i++){
 if(arg){os_log_hook_t old=os_log_set_hook(OS_LOG_TYPE_FAULT,^(os_log_type_t type,os_log_message_t msg){CHECK(type==OS_LOG_TYPE_ERROR&&os_log_get_type(msg)==type);char *s=copy_message(msg);CHECK(s&&!strcmp(s,"worker 17"));free(s);__sync_fetch_and_add(&calls,1);});if(old)Block_release(old);}
 EMIT(OS_LOG_TYPE_ERROR,"worker %{public}d",17);
 }}return NULL;}
int main(void){setbuf(stdout,NULL);@autoreleasepool{
 void *provider=dlopen("/usr/lib/libDarlingMetrics.dylib",RTLD_LAZY|RTLD_LOCAL);CHECK(provider);copy_message=dlsym(provider,"os_log_copy_message_string");CHECK(copy_message);
 os_log_type_t (*native_type)(os_log_message_t)=dlsym(provider,"os_log_get_type");CHECK(native_type);
 for(unsigned i=0;i<256;i++){struct os_log_message_s msg={.trace_id=UINT64_C(0xfedcba9876540004)|((uint64_t)i<<8)};CHECK(os_log_get_type(&msg)==native_type(&msg));}
 Dl_info image;CHECK(dladdr((void *)os_log_get_type,&image)&&strstr(image.dli_fname,EXPECTED_LIBTRACE_PATH));
 CHECK(os_log_set_fault_callback(NULL)==os_log_fault_default_callback);
 CHECK(os_log_set_fault_callback(fault)==os_log_fault_default_callback);CHECK(os_log_set_fault_callback(NULL)==fault);
 test_log=os_log_create("org.darling.log-hook","actual-events");CHECK(test_log);
 HookOwner *owner=[HookOwner new];
 CHECK(!os_log_set_hook(OS_LOG_TYPE_ERROR,^(os_log_type_t type,os_log_message_t msg){
  CHECK([owner identity]==42);CHECK(os_log_get_type(msg)==type);CHECK(!strcmp(msg->subsystem,"org.darling.log-hook"));CHECK(!strcmp(msg->category,"actual-events"));CHECK(!msg->privdata&&!msg->privdata_sz);char *value=copy_message(msg);printf("HOOK_TEXT %s\n",value?value:"<NULL>");CHECK(value&&expected&&!strcmp(value,expected));free(value);__sync_fetch_and_add(&calls,1);
 }));[owner release];CHECK(!destructions);
 EMIT(OS_LOG_TYPE_DEBUG,"below threshold");EMIT(OS_LOG_TYPE_INFO,"below threshold");EMIT(OS_LOG_TYPE_DEFAULT,"below threshold");CHECK(!calls);
 CASE("literal 100%","literal 100%%");
 CASE("integer=-77","integer=%{public}d",-77);
 CASE("18446744073709551615 1.25","%{public}llu %{public}.2f",UINT64_MAX,1.25);
 CASE("text=hello","text=%{public}s","hello");
 CASE("abc","%{public}.*s",3,"abcdef");
 CASE("","%{public}.*s",0,(const char *)1);
 CASE("你好 Linux","%{public}@",@"你好 Linux");
 CASE("<private>","%{private}s","must-not-appear");
 CASE("<private>","%s","default-private");
 CASE("<private>","%{private}d",1234);
 CASE("(null)","%{public}s",(const char *)NULL);
 CASE("wide","%{public}S",L"wide");
 errno=ENOENT;CASE("No such file or directory","%m");
 expected="public macro -77";unsigned macro_calls=calls;
 os_log_error(test_log,"public macro %{public}d",-77);CHECK(calls==macro_calls+1);
 expected="fault 42";EMIT(OS_LOG_TYPE_FAULT,"fault %{public}d",42);CHECK(faults==1);
 macro_calls=calls;os_log_fault(test_log,"fault %{public}d",42);CHECK(calls==macro_calls+1&&faults==2);
 CHECK(os_log_set_fault_callback(os_log_fault_default_callback)==fault);CHECK(os_log_set_fault_callback(NULL)==os_log_fault_default_callback);
 unsigned old=calls;uint8_t malformed[]={0,1,2};_os_log_impl(NULL,test_log,OS_LOG_TYPE_ERROR,"%{public}d",malformed,sizeof(malformed));CHECK(calls==old);
 os_log_hook_t previous=os_log_set_hook(OS_LOG_TYPE_DEBUG,^(os_log_type_t type,os_log_message_t msg){CHECK(os_log_get_type(msg)==type);__sync_fetch_and_add(&calls,1);});CHECK(previous&&destructions==0);Block_release(previous);CHECK(destructions==1);
 old=calls;EMIT(OS_LOG_TYPE_DEBUG,"debug enabled");CHECK(calls==old+1);
 previous=os_log_set_hook(OS_LOG_TYPE_FAULT,^(os_log_type_t type,os_log_message_t msg){__sync_fetch_and_add(&calls,1);});CHECK(previous);Block_release(previous);
 old=calls;EMIT(OS_LOG_TYPE_DEBUG,"historical minimum");CHECK(calls==old+1);
 previous=os_log_set_hook(OS_LOG_TYPE_DEFAULT,^(os_log_type_t type,os_log_message_t msg){__sync_fetch_and_add(&calls,1);EMIT(OS_LOG_TYPE_ERROR,"nested");});CHECK(previous);Block_release(previous);
 old=calls;EMIT(OS_LOG_TYPE_ERROR,"outer");CHECK(calls==old+1);
 previous=os_log_set_hook(OS_LOG_TYPE_DEBUG,^(os_log_type_t type,os_log_message_t msg){CHECK(type==OS_LOG_TYPE_ERROR);char *s=copy_message(msg);CHECK(s&&!strcmp(s,"worker 17"));free(s);__sync_fetch_and_add(&calls,1);});CHECK(previous);Block_release(previous);
 old=calls;pthread_t threads[8];for(unsigned i=0;i<8;i++)CHECK(!pthread_create(&threads[i],NULL,worker,(void *)(uintptr_t)(i&1)));for(unsigned i=0;i<8;i++)CHECK(!pthread_join(threads[i],NULL));CHECK(calls==old+400);
 previous=os_log_set_hook(OS_LOG_TYPE_FAULT,^(os_log_type_t type,os_log_message_t msg){});CHECK(previous);Block_release(previous);
 [(id)test_log release];printf("SOURCE_LOG_HOOK_REAL_SERIALIZED_EVENTS_LEVELS_OWNERSHIP_REENTRANCY_FAULT_AND_CONCURRENCY_OK checks=%u calls=%u\n",checks,calls);return 0;
}}
