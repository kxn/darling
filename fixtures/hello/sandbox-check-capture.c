/* Test-process interposition only. Production builds do not link this file. */
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <assert.h>
int capture_enabled,capture_return,capture_error,capture_calls;
uint64_t capture_decision,capture_words[20],capture_pair[2];
char capture_operation[160];int capture_has_operation;
extern int __mac_syscall(const char *,int,void *);
static int capture_mac(const char *policy,int operation,void *arguments) {
    if(!capture_enabled)return __mac_syscall(policy,operation,arguments);
    assert(!strcmp(policy,"Sandbox") && operation==2);capture_calls++;
    uint64_t *words=arguments;memcpy(capture_words,words,sizeof(capture_words));
    assert(*(uint64_t*)(uintptr_t)words[0]==0);
    capture_has_operation=words[2]!=0;capture_operation[0]=0;
    if(words[2]){assert(strlen((char*)(uintptr_t)words[2])<sizeof(capture_operation));strcpy(capture_operation,(char*)(uintptr_t)words[2]);}
    capture_pair[0]=capture_pair[1]=0;
    if(words[3]==35 || words[3]==241){memcpy(capture_pair,(void*)(uintptr_t)words[4],16);capture_words[4]=0;}
    capture_words[0]=capture_words[2]=0;
    *(uint64_t*)(uintptr_t)words[0]=capture_decision;
    if(capture_return)errno=capture_error;
    return capture_return;
}
__attribute__((used,section("__DATA,__interpose")))
static const struct {const void *replacement,*original;} entries[]={{(void*)capture_mac,(void*)__mac_syscall}};
