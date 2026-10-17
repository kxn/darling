#include <sys/types.h>
#include <sys/stat.h>
#include <sys/ioctl.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <poll.h>
#include <unistd.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
static unsigned checks;
#define CHECK(x) do { ++checks;if(!(x)){fprintf(stderr,"FAIL line=%d %s errno=%d\n",__LINE__,#x,errno);exit(1);} } while(0)
struct Clone {int8_t* actions;int32_t count,depth;int32_t* output;};
static uint16_t u16(const unsigned char* p) {uint16_t v;memcpy(&v,p,2);return v;}
static uint32_t u32(const unsigned char* p) {uint32_t v;memcpy(&v,p,4);return v;}
static uint64_t u64(const unsigned char* p) {uint64_t v;memcpy(&v,p,8);return v;}
static void file(const char* p) {int fd=open(p,O_CREAT|O_WRONLY|O_EXCL,0600);CHECK(fd>=0);CHECK(write(fd,"real bytes",10)==10);CHECK(close(fd)==0);}
static void event(int fd,int type,const char* one,const char* two,uint64_t inode,int compact) {
    struct pollfd p={fd,POLLIN,0};CHECK(poll(&p,1,5000)==1);
    unsigned char bytes[32768];
    CHECK(read(fd,bytes,1)==0); // first event must remain queued
    ssize_t n=read(fd,bytes,sizeof bytes);CHECK(n>=10);
    CHECK((int)u32(bytes)==type);CHECK(u32(bytes+4)==0); // inotify cannot identify the writer PID
    unsigned paths=0,ids=0,at=8;int done=0,saw_compact=0;
    while(at<(unsigned)n) {
        unsigned t=u16(bytes+at);at+=2;
        if(t==0xb33f) {done=1;break;}
        CHECK(at+2<=(unsigned)n);unsigned count=u16(bytes+at);at+=2;CHECK(at+count<=(unsigned)n);
        if(t==2) {CHECK(bytes[at+count-1]==0);CHECK(!strcmp((char*)bytes+at,paths?two:one));paths++;}
        if(t==7 || t==12) {CHECK(count==(t==7?8:24));CHECK(u64(bytes+at)==inode);ids++;saw_compact|=t==12;}
        at+=count;
    }
    CHECK(done && at==(unsigned)n);CHECK(paths==(two?2:1));CHECK(ids==1);CHECK(saw_compact==compact);
}
int main(int argc,char** argv) {
    if(argc==3 && !strcmp(argv[1],"--exec")) {
        int fd=atoi(argv[2]);CHECK(ioctl(fd,0x20007365,0)==0);puts("FSEVENTS_EXEC_INHERITED_DESCRIPTOR_OK");return 0;
    }
    char root[PATH_MAX],path[PATH_MAX],from[PATH_MAX],to[PATH_MAX];
    snprintf(root,sizeof root,"/tmp/darling-raw-fsevents-%d",getpid());CHECK(mkdir(root,0700)==0);
    CHECK(realpath(root,path));strcpy(root,path);
    snprintf(path,sizeof path,"%s/delete",root);file(path);struct stat removed;CHECK(lstat(path,&removed)==0);
    snprintf(from,sizeof from,"%s/from",root);snprintf(to,sizeof to,"%s/to",root);file(from);
    struct stat moved;CHECK(lstat(from,&moved)==0);
    int control=open("/dev/fsevents",O_RDONLY|O_CLOEXEC);CHECK(control>=0);CHECK(fcntl(control,F_GETFD)&FD_CLOEXEC);
    int8_t actions[16]={0};actions[1]=actions[3]=1;int stream=-1;
    struct Clone args={actions,16,8192,&stream};
    CHECK(ioctl(control,0x80187301,(void*)1)==-1 && errno==EFAULT);
    args.count=65;CHECK(ioctl(control,0x80187301,&args)==-1 && errno==EINVAL);args.count=16;
    actions[0]=1;CHECK(ioctl(control,0x80187301,&args)==-1 && errno==EOPNOTSUPP);CHECK(stream==-1);actions[0]=0;
    CHECK(ioctl(control,0x80187301,&args)==0);CHECK(stream>=0);
    CHECK(unlink(path)==0);event(stream,1,path,0,removed.st_ino,0);
    CHECK(rename(from,to)==0);event(stream,3,from,to,moved.st_ino,0);
    CHECK(ioctl(stream,0x40087367,0)==-1 && errno==EOPNOTSUPP);
    CHECK(ioctl(stream,0x800c7364,(void*)1)==-1 && errno==EFAULT);
    int duplicate=dup(stream);CHECK(duplicate>=0);CHECK(close(stream)==0);
    pid_t child=fork();CHECK(child>=0);
    if(!child) {_exit(ioctl(duplicate,0x20007366,0)?1:0);}
    int status;CHECK(waitpid(child,&status,0)==child);CHECK(WIFEXITED(status)&&WEXITSTATUS(status)==0);
    child=fork();CHECK(child>=0);
    if(!child) {char fd[32];snprintf(fd,sizeof fd,"%d",duplicate);execl(argv[0],argv[0],"--exec",fd,(char*)0);_exit(127);}
    CHECK(waitpid(child,&status,0)==child);CHECK(WIFEXITED(status)&&WEXITSTATUS(status)==0);
    CHECK(unlink(to)==0);event(duplicate,1,to,0,moved.st_ino,1);
    CHECK(fcntl(duplicate,F_SETFL,O_NONBLOCK)==0);
    char byte;CHECK(read(duplicate,&byte,1)==-1 && errno==EAGAIN);
    CHECK(close(duplicate)==0);CHECK(close(control)==0);CHECK(rmdir(root)==0);
    printf("FSEVENTS_DEVICE_NATIVE_ABI_REAL_DELETE_RENAME_DUP_FORK_EXEC_OK checks=%u\n",checks);return 0;
}
