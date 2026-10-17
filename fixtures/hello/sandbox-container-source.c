#include <assert.h>
#include <dlfcn.h>
#include <errno.h>
#include <mach/mach.h>
#include <mach/task_info.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
typedef int (*container_fn)(audit_token_t, char *, size_t);
int main(int argc, char **argv) {
    assert(argc==4 && sizeof(audit_token_t)==32);setbuf(stdout,NULL);
    void *system=dlopen(argv[1],RTLD_LAZY);assert(system);
    void *native=dlopen(argv[2],RTLD_LAZY);assert(native);
    container_fn source=dlsym(system,"sandbox_container_path_for_audit_token");
    container_fn original=dlsym(native,"sandbox_container_path_for_audit_token");
    int (*mac)(const char *,int,void*)=dlsym(system,"__mac_syscall");assert(source&&original&&mac);
    Dl_info owner;assert(dladdr((void*)source,&owner)&&!strcmp(owner.dli_fname,argv[3]));
    assert(dladdr((void*)original,&owner)&&!strcmp(owner.dli_fname,argv[2]));
    audit_token_t token;mach_msg_type_number_t count=TASK_AUDIT_TOKEN_COUNT;
    kern_return_t kr=task_info(mach_task_self(),TASK_AUDIT_TOKEN,(task_info_t)&token,&count);
    printf("TASK_AUDIT_TOKEN_STATUS %d count=%u values=",kr,count);
    for(unsigned i=0;i<8;i++)printf(" %u",token.val[i]);puts("");
    assert(kr==KERN_SUCCESS && count==TASK_AUDIT_TOKEN_COUNT);
    assert(token.val[5]==getpid());
    assert(token.val[1]==geteuid()&&token.val[2]==getegid()&&token.val[3]==getuid()&&token.val[4]==getgid());
    unsigned checked=0;
    const size_t sizes[]={0,1,8,1024};
    for(unsigned kind=0;kind<3;kind++) for(unsigned n=0;n<4;n++) {
        audit_token_t input=token;
        if(kind==1)memset(&input,0xff,sizeof(input));
        if(kind==2)input.val[7]^=0x80000000;
        struct {uint64_t before;char path[1024];uint64_t after;} a,b;
        memset(&a,0xa7,sizeof(a));memset(&b,0xa7,sizeof(b));
        errno=0;int result=source(input,a.path,sizes[n]);int error=errno;
        errno=0;int expected=original(input,b.path,sizes[n]);int expected_error=errno;
        assert(result==expected && error==expected_error && !memcmp(&a,&b,sizeof(a)));
        assert(result==-1 && error==ENOPOLICY);
        uint64_t args[5]={input.val[5],input.val[7],(uintptr_t)b.path,sizes[n],1};
        errno=0;assert(mac("Sandbox",4,args)==result && errno==error);
        checked++;
    }
    puts("SOURCE_SANDBOX_CONTAINER_REAL_TASK_AUDIT_TOKEN_PID_AND_CREDENTIAL_FIELDS_OK");
    printf("SOURCE_SANDBOX_CONTAINER_NATIVE_AND_REAL_MAC_ERRORS_UNCHANGED_BUFFER_OK %u\n",checked);
}
