#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <dlfcn.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/xattr.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <spawn.h>
extern char **environ;
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"FAIL line=%d %s errno=%d\n",__LINE__,#x,errno);exit(1);}}while(0)
typedef void* object;
static object(*alloc)(void);static void(*release)(object);static int(*set_id)(object,const char*),(*set_flags)(object,unsigned),(*apply)(object),(*read_self)(object);static unsigned(*get_flags)(object);static int(*set_meta)(object,const void*,size_t);
static const char *identity="org.darling.quarantine-vfs-test";
static void functions(void){
    alloc=dlsym(RTLD_DEFAULT,"_qtn_proc_alloc");release=dlsym(RTLD_DEFAULT,"_qtn_proc_free");set_id=dlsym(RTLD_DEFAULT,"_qtn_proc_set_identifier");set_flags=dlsym(RTLD_DEFAULT,"_qtn_proc_set_flags");apply=dlsym(RTLD_DEFAULT,"_qtn_proc_apply_to_self");read_self=dlsym(RTLD_DEFAULT,"_qtn_proc_init_with_self");get_flags=dlsym(RTLD_DEFAULT,"_qtn_proc_get_flags");set_meta=dlsym(RTLD_DEFAULT,"_qtn_proc_set_metadata");CHECK(alloc&&release&&set_id&&set_flags&&apply&&read_self&&get_flags&&set_meta);
}
static void path(char *out,const char *base,const char *name){snprintf(out,1024,"%s/%s",base,name);}
static unsigned label(const char *file,char *out){
    ssize_t n=getxattr(file,"com.apple.quarantine",out,1023,0,0);CHECK(n>0&&n<1024);out[n]=0;unsigned flags;CHECK(sscanf(out,"%x;",&flags)==1);return flags;
}
static void create(const char *file,const char *data){int fd=open(file,O_WRONLY|O_CREAT|O_EXCL,0600);CHECK(fd>=0);CHECK(write(fd,data,strlen(data))==(ssize_t)strlen(data));CHECK(close(fd)==0);}
static void copy(const char *from,const char *to){
    int in=open(from,O_RDONLY),out=open(to,O_WRONLY|O_CREAT|O_EXCL,0700);CHECK(in>=0&&out>=0);char data[4096];ssize_t n;
    while((n=read(in,data,sizeof(data)))>0)CHECK(write(out,data,n)==n);CHECK(n==0);CHECK(close(in)==0&&close(out)==0);
}
static void denied(const char *file){
    pid_t child=fork();CHECK(child>=0);if(!child){execl(file,file,NULL);_exit(errno==EPERM?0:7);}int status;CHECK(waitpid(child,&status,0)==child&&WIFEXITED(status)&&WEXITSTATUS(status)==0);
    char *args[]={(char*)file,NULL};pid_t pid;CHECK(posix_spawn(&pid,file,NULL,NULL,args,environ)==EPERM);
}
static void run(const char *file,const char *output){
    char *args[]={(char*)file,(char*)output,NULL};pid_t pid;CHECK(posix_spawn(&pid,file,NULL,NULL,args,environ)==0);int status;CHECK(waitpid(pid,&status,0)==pid&&WIFEXITED(status)&&WEXITSTATUS(status)==0);
}
static void restricted(const char *base,const char *leaf){
    object p=alloc();CHECK(p);CHECK(set_id(p,identity)==0&&set_flags(p,6)==0&&set_meta(p,"metadata-v1",11)==0);CHECK(apply(p)==0);release(p);
    p=alloc();CHECK(p&&read_self(p)==0&&get_flags(p)==6);release(p);
    char file[1024],data[1024],other[1024];path(file,base,"new");create(file,"created");CHECK(label(file,data)==0x86);CHECK(strstr(data,identity)&&strstr(data,"metadata-v1"));
    int fd=open(file,O_RDONLY);CHECK(fd>=0);errno=0;CHECK(fsetxattr(fd,"com.apple.quarantine","0000;00000000;x;",16,0,0)==-1&&errno==EPERM);errno=0;CHECK(setxattr(file,"com.apple.quarantine","0000;00000000;x;",16,0,0)==-1&&errno==EPERM);
    CHECK(setxattr(file,"user.com.apple.quarantine","shadow",6,0,0)==0);CHECK(label(file,data)==0x86);
    errno=0;CHECK(fsetxattr(fd,(const char*)1,"x",1,0,0)==-1&&errno==EFAULT);
    CHECK(fremovexattr(fd,"com.apple.quarantine",0)==0);CHECK(label(file,data)==0x82);CHECK(!strstr(data,"metadata-v1"));CHECK(close(fd)==0);
    path(file,base,"existing");fd=open(file,O_WRONLY);CHECK(fd>=0);CHECK(close(fd)==0);CHECK(label(file,data)==0x82);CHECK(!strstr(data,"metadata-v1"));
    path(file,base,"directory");CHECK(mkdir(file,0700)==0);CHECK(label(file,data)==0x86);CHECK(strstr(data,";00000000;")!=NULL);
    path(file,base,"rename-source");create(file,"rename");path(other,base,"renamed");CHECK(rename(file,other)==0);CHECK(label(other,data)==0x82);CHECK(strstr(data,"metadata-v1"));
    path(file,base,"hard");copy(leaf,file);CHECK(label(file,data)==0x86);denied(file);
    path(other,base,"hard-link");CHECK(link(file,other)==0);CHECK(label(other,data)==0x86);
    path(other,base,"exec-inherited");run(leaf,other);CHECK(label(other,data)==0x86);CHECK(strstr(data,identity));
    pid_t forked=fork();CHECK(forked>=0);if(!forked){path(other,base,"fork-inherited");create(other,"fork");_exit(0);}int status;CHECK(waitpid(forked,&status,0)==forked&&WIFEXITED(status)&&WEXITSTATUS(status)==0);
    path(other,base,"fork-inherited");CHECK(label(other,data)==0x86);
    p=alloc();CHECK(p&&set_id(p,"other")==0&&set_flags(p,6)==0);CHECK(apply(p)==ENOTSUP);CHECK(set_flags(p,0)==0&&apply(p)==ENOTSUP);release(p);
    printf("QUARANTINE_VFS_RESTRICTED_PROCESS_FILE_EVENTS_AND_EXEC_CHECKS_OK checks=%u\n",checks);
}
int main(int argc,char **argv){
    setbuf(stdout,NULL);CHECK(argc==4);functions();
    object p=alloc();CHECK(p&&set_id(p,identity)==0&&set_flags(p,6)==0);
    if(!strcmp(argv[3],"old-kernel-control")){CHECK(apply(p)==ENOTSUP);release(p);puts("QUARANTINE_OLD_KERNEL_CANNOT_ACKNOWLEDGE_UNENFORCED_POLICY_OK");return 0;}
    release(p);p=alloc();errno=0;CHECK(p&&read_self(p)==-1&&errno==ENOATTR);release(p);
    char file[1024],data[1024],other[1024];path(file,argv[1],"existing");create(file,"existing");errno=0;CHECK(getxattr(file,"com.apple.quarantine",data,sizeof(data),0,0)==-1&&errno==ENOATTR);
    pid_t child=fork();CHECK(child>=0);if(!child){restricted(argv[1],argv[2]);_exit(0);}int status;CHECK(waitpid(child,&status,0)==child&&WIFEXITED(status)&&WEXITSTATUS(status)==0);
    path(file,argv[1],"hard");denied(file);
    const char *approved="0044;00000000;parent;";CHECK(setxattr(file,"com.apple.quarantine",approved,strlen(approved),0,0)==0);denied(file);
    const char *malformed[]={"0000;garbage;agent;","0000;00000000","00000;00000000;agent;","0000","","0004;0;agent;"};
    for(unsigned i=0;i<sizeof(malformed)/sizeof(*malformed);i++){CHECK(setxattr(file,"com.apple.quarantine",malformed[i],strlen(malformed[i]),0,0)==0);denied(file);}
    const char *valid[]={"0;0;agent"," 0; 1;agent;","0x40;0xff;agent;","0000;123456789;agent;","-0;0;agent;","+0;0;agent;"};
    for(unsigned i=0;i<sizeof(valid)/sizeof(*valid);i++){CHECK(setxattr(file,"com.apple.quarantine",valid[i],strlen(valid[i]),0,0)==0);run(file,NULL);}
    CHECK(removexattr(file,"com.apple.quarantine",0)==0);path(other,argv[1],"parent-unconfined-exec");run(file,other);errno=0;CHECK(getxattr(other,"com.apple.quarantine",data,sizeof(data),0,0)==-1&&errno==ENOATTR);
    p=alloc();errno=0;CHECK(p&&read_self(p)==-1&&errno==ENOATTR);release(p);
    puts("QUARANTINE_VFS_REAL_PERSISTED_LABELS_KERNEL_PAIRING_FORK_EXEC_AND_UNCONFINED_CONTROL_OK");
}
