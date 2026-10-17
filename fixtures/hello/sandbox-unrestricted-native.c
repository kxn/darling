#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <mach/mach.h>
#include <mach/task_info.h>
#include <servers/bootstrap.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>
struct profile {const char *builtin;const void *data;uint64_t length;};
static unsigned checks;
#define CHECK(x) do {checks++;if (!(x)) {fprintf(stderr,"FAIL line=%d expression=%s errno=%d\n",__LINE__,#x,errno);exit(1);}} while(0)
static int (*query)(int,const char *,int,...);
static int (*by_audit)(audit_token_t,const char *,int,...);
static const char *operations[]={
#include "../../vendor/darlingserver/src/sandbox-operation-names.inc"
};
static audit_token_t audit(void) {
    audit_token_t t;mach_msg_type_number_t n=TASK_AUDIT_TOKEN_COUNT;
    CHECK(task_info(mach_task_self(),TASK_AUDIT_TOKEN,(task_info_t)&t,&n)==KERN_SUCCESS && n==TASK_AUDIT_TOKEN_COUNT);return t;
}
int main(int argc,char **argv) {
    setbuf(stdout,NULL);query=dlsym(RTLD_DEFAULT,"sandbox_check");by_audit=dlsym(RTLD_DEFAULT,"sandbox_check_by_audit_token");CHECK(query&&by_audit);
    if (argc==3 && !strcmp(argv[1],"--exec")) {
        int fd=atoi(argv[2]);CHECK(query(getpid(),NULL,0)==1);audit_token_t t=audit();CHECK(write(fd,&t,sizeof t)==sizeof t);
        puts("UNRESTRICTED_NATIVE_PROFILE_SURVIVES_EXEC_OK");return 0;
    }
    CHECK(query(getpid(),NULL,0)==0);
    void (*notify)(void)=dlsym(RTLD_DEFAULT,"_xpc_runtime_process_has_entered_sandbox");CHECK(notify);
    Dl_info owner={0};CHECK(dladdr((void *)notify,&owner) && owner.dli_fname && strstr(owner.dli_fname,"libxpc.dylib"));
    printf("UNRESTRICTED_NATIVE_NOTIFY_OWNER %s\n",owner.dli_fname);notify();CHECK(query(getpid(),NULL,0)==0);
    void *library=dlopen("/usr/lib/libsandbox.1.dylib",RTLD_LAZY|RTLD_LOCAL);CHECK(library);
    void *(*params)(void)=dlsym(library,"sandbox_create_params");
    int (*set)(void*,const char*,const char*)=dlsym(library,"sandbox_set_param");
    void (*free_params)(void*)=dlsym(library,"sandbox_free_params");
    struct profile *(*compile)(const char*,void*,char**)=dlsym(library,"sandbox_compile_string");
    struct profile *(*named)(const char*,void*,char**)=dlsym(library,"sandbox_compile_named");
    int (*apply)(struct profile*)=dlsym(library,"sandbox_apply");void (*release)(void*)=dlsym(library,"sandbox_free_profile");
    CHECK(params&&set&&free_params&&compile&&named&&apply&&release);void *p=params();CHECK(p);
    CHECK(set(p,"DARWIN_USER_TEMP_DIR","/tmp/com.apple.coreservicesd")==0 && set(p,"DARWIN_USER_CACHE_DIR","/root/.cache/com.apple.coreservicesd")==0);
    char *error=NULL;struct profile *deny=compile("(version 1)(deny default)",p,&error);CHECK(deny && !error);
    struct profile *core=named("com.apple.coreservicesd",p,&error);CHECK(core && !error);
    struct profile *defaults=compile("(version 1)(allow default)",p,&error);CHECK(defaults && !error);
    struct profile *allow=compile("(version 1)(set! *apply-implicit-policy* #f)(allow default)(allow file-write-setugid job-creation system-kas-info storage-class-map)",p,&error);
    if (!allow || error) fprintf(stderr,"EXPLICIT_POLICY_COMPILE_ERROR %s\n",error?error:"nil");
    CHECK(allow && !error);
    CHECK(!allow->builtin && allow->length>=16);
    FILE *dump=fopen("/Volumes/SystemRoot/workspace/runtime/unrestricted-sandbox-tests/explicit-profile.bin","wb");
    CHECK(dump && fwrite(allow->data,1,allow->length,dump)==allow->length && fclose(dump)==0);
    errno=0;CHECK(apply(deny)==-1 && errno==ENOTSUP && query(getpid(),NULL,0)==0);
    errno=0;CHECK(apply(core)==-1 && errno==ENOTSUP && query(getpid(),NULL,0)==0);
    errno=0;CHECK(apply(defaults)==-1 && errno==ENOTSUP && query(getpid(),NULL,0)==0);
    CHECK(apply(allow)==0 && query(getpid(),NULL,0)==1);
    errno=0;CHECK(apply(allow)==-1 && errno==EPERM && query(getpid(),NULL,0)==1);
    errno=0;CHECK(apply(core)==-1 && errno==ENOTSUP && query(getpid(),NULL,0)==1);
    release(allow);release(defaults);release(core);release(deny);free_params(p);
    CHECK(sizeof operations/sizeof operations[0]==198);
    for(unsigned i=0;i<198;i++)CHECK(query(getpid(),operations[i],0)==0);
    errno=0;CHECK(query(getpid(),"not-a-native-operation",0)==-1 && errno==EINVAL);
    char directory[]="/tmp/unrestricted-sandbox-XXXXXX";CHECK(mkdtemp(directory));
    char a[1024],b[1024];snprintf(a,sizeof a,"%s/a",directory);snprintf(b,sizeof b,"%s/b",directory);
    int fd=open(a,O_CREAT|O_WRONLY,0600);CHECK(fd>=0 && write(fd,"data",4)==4 && close(fd)==0);
    CHECK(rename(a,b)==0 && unlink(b)==0 && rmdir(directory)==0);
    mach_port_t receiver,found;char name[128];snprintf(name,sizeof name,"org.linuxcode.unrestricted.%d",getpid());
    CHECK(mach_port_allocate(mach_task_self(),MACH_PORT_RIGHT_RECEIVE,&receiver)==KERN_SUCCESS);
    CHECK(mach_port_insert_right(mach_task_self(),receiver,receiver,MACH_MSG_TYPE_MAKE_SEND)==KERN_SUCCESS);
    CHECK(bootstrap_register(bootstrap_port,name,receiver)==BOOTSTRAP_SUCCESS);
    CHECK(bootstrap_look_up(bootstrap_port,name,&found)==BOOTSTRAP_SUCCESS);
    CHECK(mach_port_deallocate(mach_task_self(),found)==KERN_SUCCESS && mach_port_destroy(mach_task_self(),receiver)==KERN_SUCCESS);
    int child_ready[2],resume[2];CHECK(pipe(child_ready)==0 && pipe(resume)==0);pid_t child=fork();CHECK(child>=0);
    if (!child) {
        close(child_ready[0]);close(resume[1]);CHECK(query(getpid(),NULL,0)==1);audit_token_t before=audit();
        CHECK(write(child_ready[1],&before,sizeof before)==sizeof before);char byte;CHECK(read(resume[0],&byte,1)==1);
        char number[32];snprintf(number,sizeof number,"%d",child_ready[1]);execl(argv[0],argv[0],"--exec",number,(char*)NULL);_exit(90);
    }
    close(child_ready[1]);close(resume[0]);audit_token_t before,after;
    CHECK(read(child_ready[0],&before,sizeof before)==sizeof before && before.val[5]==(unsigned)child);
    CHECK(by_audit(before,NULL,0)==1);CHECK(write(resume[1],"x",1)==1);
    CHECK(read(child_ready[0],&after,sizeof after)==sizeof after && after.val[5]==before.val[5] && after.val[7]!=before.val[7]);
    CHECK(by_audit(after,NULL,0)==1);errno=0;CHECK(by_audit(before,NULL,0)==-1 && errno==ESRCH);
    int status;CHECK(waitpid(child,&status,0)==child && WIFEXITED(status) && WEXITSTATUS(status)==0);
    close(child_ready[0]);close(resume[1]);
    printf("UNRESTRICTED_ORIGINAL_COMPILER_APPLY_NOTIFY_QUERY_FORK_EXEC_AND_RESTRICTIVE_FAILURES_OK checks=%u\n",checks);return 0;
}
