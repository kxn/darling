#include <mach/mach.h>
#include <mach/task_info.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <sys/wait.h>
#include <dlfcn.h>
#include <limits.h>
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"FAIL %d %s errno=%d\n",__LINE__,#x,errno);exit(1);}}while(0)
typedef int(*pid_query)(int,const char*,int,...);
typedef int(*audit_query)(audit_token_t,const char*,int,...);
static audit_token_t audit(void){audit_token_t t;mach_msg_type_number_t n=TASK_AUDIT_TOKEN_COUNT;CHECK(task_info(mach_task_self(),TASK_AUDIT_TOKEN,(task_info_t)&t,&n)==KERN_SUCCESS);CHECK(n==TASK_AUDIT_TOKEN_COUNT);return t;}
int main(int argc,char **argv){
    CHECK(argc==2);setbuf(stdout,NULL);
    pid_query query=dlsym(RTLD_DEFAULT,"sandbox_check");audit_query by_audit=dlsym(RTLD_DEFAULT,"sandbox_check_by_audit_token");
    int(*mac)(const char*,int,void*)=dlsym(RTLD_DEFAULT,"__mac_syscall");CHECK(query&&by_audit&&mac);
    void *original=dlopen(argv[1],RTLD_LAZY|RTLD_LOCAL);CHECK(original);pid_query native=dlsym(original,"sandbox_check");audit_query native_audit=dlsym(original,"sandbox_check_by_audit_token");CHECK(native&&native_audit);
    audit_token_t self=audit();CHECK(self.val[5]==(unsigned)getpid());CHECK(self.val[7]!=0);
    printf("SANDBOX_REAL_AUDIT_GENERATION pid=%u version=%u\n",self.val[5],self.val[7]);
    const unsigned supported[]={0,0x40000000,0x20000000,0x10000000,0x08000000,0x78000000};
    for(unsigned i=0;i<6;i++){
        CHECK(query(getpid(),NULL,supported[i])==0);CHECK(native(getpid(),NULL,supported[i])==0);
        CHECK(query(getpid(),"file-read-data",1|supported[i],"/tmp/linuxcode-unconfined-query")==0);
        CHECK(native(getpid(),"file-read-data",1|supported[i],"/tmp/linuxcode-unconfined-query")==0);
        CHECK(by_audit(self,"file-read-data",1|supported[i],"/tmp/linuxcode-unconfined-query")==0);
        CHECK(native_audit(self,"file-read-data",1|supported[i],"/tmp/linuxcode-unconfined-query")==0);
    }
    errno=0;CHECK(query(INT_MAX,"file-read-data",1,"/tmp/x")==-1&&errno==ESRCH);
    errno=0;CHECK(query(-1,"file-read-data",1,"/tmp/x")==-1&&errno==EINVAL);
    audit_token_t stale=self;stale.val[7]^=0x80000000;errno=0;CHECK(by_audit(stale,"file-read-data",1,"/tmp/x")==-1&&errno==ESRCH);
    errno=0;CHECK(by_audit(self,"file-read-data",1|0x04000000,"/tmp/x")==-1&&errno==ENOTSUP);
    errno=0;CHECK(query(getpid(),"file-write-data",1|0x02000000,"/tmp/x")==-1&&errno==ENOTSUP);
    uint64_t value=0xa5a5a5a5a5a5a5a5ULL,args[20]={0};args[0]=(uintptr_t)&value;args[1]=getpid();args[2]=(uintptr_t)"file-read-data";args[3]=1;args[4]=(uintptr_t)"/tmp/x";
    CHECK(mac("Sandbox",2,args)==0&&value==0);
    const unsigned invalid_cases=8;
    for(unsigned i=0;i<invalid_cases;i++){
        uint64_t copy[20];memcpy(copy,args,sizeof(copy));value=0xa5a5a5a5a5a5a5a5ULL;int expected=EINVAL;
        if(i==0){copy[0]=1;expected=EFAULT;}
        if(i==1){copy[2]=1;expected=EFAULT;}
        if(i==2){copy[4]=1;expected=EFAULT;}
        if(i==3)copy[7]=1;
        if(i==4)copy[5]=4;
        if(i==5)copy[3]=999;
        if(i==6)copy[6]=99;
        if(i==7){copy[5]=0x20;expected=ENOTSUP;}
        errno=0;CHECK(mac("Sandbox",2,copy)==-1&&errno==expected);CHECK(value==0xa5a5a5a5a5a5a5a5ULL);
    }
    errno=0;CHECK(mac("Sandbox",1,args)==-1&&errno==ENOTSUP);
    errno=0;CHECK(mac("NoSuchPolicy",2,args)==-1&&errno==ENOPOLICY);
    errno=0;CHECK(mac("Sandbox",2,(void*)1)==-1&&errno==EFAULT);
    int(*init)(const char*,uint64_t,char**)=dlsym(RTLD_DEFAULT,"sandbox_init");
    int(*params)(const char*,uint64_t,const char*const*,char**)=dlsym(RTLD_DEFAULT,"sandbox_init_with_parameters");
    int(*extensions)(const char*,uint64_t,const char*const*,char**)=dlsym(RTLD_DEFAULT,"sandbox_init_with_extensions");
    void(*free_error)(char*)=dlsym(RTLD_DEFAULT,"sandbox_free_error");CHECK(init&&params&&extensions&&free_error);
    for(unsigned i=0;i<3;i++)for(unsigned with_error=0;with_error<2;with_error++){
        char *error=NULL;char **out=with_error?&error:NULL;errno=0;
        int r=i==0?init("(version 1)(deny default)",0,out):i==1?params("(version 1)(deny default)",0,NULL,out):extensions("(version 1)(deny default)",0,NULL,out);
        CHECK(r==-1&&errno==ENOTSUP);if(with_error){CHECK(error&&strstr(error,"not implemented"));free_error(error);}
        CHECK(query(getpid(),NULL,0)==0);
    }
    int ready[2],finish[2];CHECK(pipe(ready)==0&&pipe(finish)==0);pid_t child=fork();CHECK(child>=0);
    if(!child){close(ready[0]);close(finish[1]);audit_token_t t=audit();if(write(ready[1],&t,sizeof(t))!=sizeof(t))_exit(3);char c;if(read(finish[0],&c,1)!=1)_exit(4);_exit(0);}
    close(ready[1]);close(finish[0]);audit_token_t child_token;CHECK(read(ready[0],&child_token,sizeof(child_token))==sizeof(child_token));CHECK(child_token.val[5]==(unsigned)child);CHECK(child_token.val[7]!=self.val[7]);
    CHECK(by_audit(child_token,"file-read-data",1,"/tmp/x")==0);audit_token_t mixed=child_token;mixed.val[7]=self.val[7];errno=0;CHECK(by_audit(mixed,"file-read-data",1,"/tmp/x")==-1&&errno==ESRCH);
    CHECK(write(finish[1],"x",1)==1);int status;CHECK(waitpid(child,&status,0)==child&&WIFEXITED(status)&&WEXITSTATUS(status)==0);
    int result=0;for(unsigned i=0;i<100;i++){errno=0;result=by_audit(child_token,"file-read-data",1,"/tmp/x");if(result==-1&&errno==ESRCH)break;usleep(10000);}
    CHECK(result==-1&&errno==ESRCH);close(ready[0]);close(finish[1]);
    printf("SANDBOX_REGISTERED_UNCONFINED_STATE_REAL_AUDIT_LIFETIME_ERRORS_AND_UNSUPPORTED_PROFILES_OK checks=%u\n",checks);
}
