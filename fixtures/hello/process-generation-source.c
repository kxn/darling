#include <mach/mach.h>
#include <mach/task_info.h>
#include <libproc.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <sys/wait.h>
#include <dlfcn.h>
/* Private XNU proc_info.h ABI; the public Xcode SDK omits this structure. */
struct unique_info {
    uint8_t uuid[16];
    uint64_t unique, parent_unique;
    int32_t version;
    uint32_t reserve2;
    uint64_t reserve3, reserve4;
};
_Static_assert(sizeof(struct unique_info)==56,"XNU unique-info ABI");
struct identity { audit_token_t token; struct unique_info info; };
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"FAIL %d %s errno=%d\n",__LINE__,#x,errno);exit(1);}}while(0)
static struct identity identity(pid_t pid) {
    struct identity result={0};
    CHECK(proc_pidinfo(pid,17,0,&result.info,sizeof(result.info))==sizeof(result.info));
    CHECK(result.info.version!=0);
    CHECK(result.info.reserve2==0&&result.info.reserve3==0&&result.info.reserve4==0);
    if(pid==getpid()) {
        mach_msg_type_number_t count=TASK_AUDIT_TOKEN_COUNT;
        CHECK(task_info(mach_task_self(),TASK_AUDIT_TOKEN,(task_info_t)&result.token,&count)==KERN_SUCCESS);
        CHECK(count==TASK_AUDIT_TOKEN_COUNT);
        CHECK(result.token.val[5]==(uint32_t)pid);
        CHECK(result.token.val[7]==(uint32_t)result.info.version);
    }
    return result;
}
static void send_identity(int fd) {
    struct identity value=identity(getpid());
    CHECK(write(fd,&value,sizeof(value))==sizeof(value));
}
static void wait_finish(int fd) { char c;CHECK(read(fd,&c,1)==1); }
int main(int argc,char **argv) {
    setbuf(stdout,NULL);
    if(argc==4&&!strcmp(argv[1],"--exec-child")) {
        send_identity(atoi(argv[2]));wait_finish(atoi(argv[3]));return 0;
    }
    CHECK(argc==1);
    int (*by_audit)(audit_token_t,const char*,int,...)=dlsym(RTLD_DEFAULT,"sandbox_check_by_audit_token");CHECK(by_audit);
    struct identity self=identity(getpid());
    struct unique_info small;errno=0;
    CHECK(proc_pidinfo(getpid(),17,0,&small,sizeof(small)-1)==0&&errno==ENOSPC);
    for(unsigned iteration=0;iteration<4;iteration++) {
        int ready[2],finish[2];CHECK(pipe(ready)==0&&pipe(finish)==0);
        pid_t child=fork();CHECK(child>=0);
        if(!child) {
            close(ready[0]);close(finish[1]);
            struct identity before=identity(getpid());
            CHECK(before.info.version!=self.info.version);
            CHECK(before.info.parent_unique==self.info.unique);
            errno=0;CHECK(execl("/no-such-linuxcode-executable","missing",NULL)==-1&&errno==ENOENT);
            struct identity after_failure=identity(getpid());
            CHECK(after_failure.info.version==before.info.version&&after_failure.info.unique==before.info.unique);
            send_identity(ready[1]);
            char out[24],in[24];snprintf(out,sizeof(out),"%d",ready[1]);snprintf(in,sizeof(in),"%d",finish[0]);
            execl(argv[0],argv[0],"--exec-child",out,in,NULL);
            perror("execl self");_exit(2);
        }
        close(ready[1]);close(finish[0]);
        struct identity before,after;
        CHECK(read(ready[0],&before,sizeof(before))==sizeof(before));
        CHECK(read(ready[0],&after,sizeof(after))==sizeof(after));
        CHECK(before.token.val[5]==(uint32_t)child&&after.token.val[5]==(uint32_t)child);
        CHECK(before.info.version!=self.info.version&&after.info.version!=before.info.version);
        CHECK(before.info.unique==after.info.unique&&before.info.parent_unique==after.info.parent_unique);
        struct identity queried=identity(child);
        CHECK(queried.info.version==after.info.version&&queried.info.unique==after.info.unique);
        CHECK(by_audit(after.token,"file-read-data",1,"/tmp/linuxcode-generation")==0);
        errno=0;CHECK(by_audit(before.token,"file-read-data",1,"/tmp/linuxcode-generation")==-1&&errno==ESRCH);
        CHECK(identity(getpid()).info.version==self.info.version);
        CHECK(write(finish[1],"x",1)==1);int status;
        CHECK(waitpid(child,&status,0)==child&&WIFEXITED(status)&&WEXITSTATUS(status)==0);
        errno=0;CHECK(proc_pidinfo(child,17,0,&small,sizeof(small))==0&&errno==ESRCH);
        close(ready[0]);close(finish[1]);
    }
    printf("PROCESS_GENERATION_LIBPROC_AUDIT_FORK_EXEC_FAILED_EXEC_STALE_TOKEN_AND_SIZE_OK checks=%u iterations=4\n",checks);
}
