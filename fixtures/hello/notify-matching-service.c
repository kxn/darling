#include <notify.h>
#include <mach/mach.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>
static unsigned checks;
#define check(c) do{++checks;if(!(c)){fprintf(stderr,"NOTIFY_FAIL line=%d check=%u\n",__LINE__,checks);exit(1);}}while(0)
int main(int argc,char** argv){
 if(argc==3 && !strcmp(argv[1],"--post")){uint32_t status=notify_post(argv[2]);printf("NOTIFY_CHILD_POST status=%u\n",status);return status?1:0;}
 setbuf(stdout,NULL);Dl_info info={0};check(dladdr((void*)notify_register_mach_port,&info));printf("NOTIFY_PROVIDER %s\n",info.dli_fname);
 char name[128];snprintf(name,sizeof(name),"org.linuxcode.notify.%d",getpid());mach_port_t port=0;int token=-1;
 uint32_t status=notify_register_mach_port(name,&port,0,&token);printf("NOTIFY_REGISTER status=%u port=%u token=%d\n",status,port,token);check(!status&&port&&token>=0);
 pid_t child=fork();check(child>=0);if(!child){execl(argv[0],argv[0],"--post",name,NULL);_exit(127);}int code=0;check(waitpid(child,&code,0)==child&&WIFEXITED(code)&&WEXITSTATUS(code)==0);
 union{mach_msg_header_t h;unsigned char buffer[512];} message={0};
 check(!mach_msg(&message.h,MACH_RCV_MSG|MACH_RCV_TIMEOUT,0,sizeof(message),port,2000,0));check(message.h.msgh_id==token);
 int first=token;char second[128];snprintf(second,sizeof(second),"org.linuxcode.notify.reuse.%d",getpid());
 check(!notify_register_mach_port(second,&port,NOTIFY_REUSE,&token));check(token!=first);check(!notify_post(second));
 check(!mach_msg(&message.h,MACH_RCV_MSG|MACH_RCV_TIMEOUT,0,sizeof(message),port,2000,0));check(message.h.msgh_id==token);
 check(!notify_cancel(token));check(!notify_post(second));
 check(mach_msg(&message.h,MACH_RCV_MSG|MACH_RCV_TIMEOUT,0,sizeof(message),port,50,0)==MACH_RCV_TIMED_OUT);
 check(!notify_post(name));check(!mach_msg(&message.h,MACH_RCV_MSG|MACH_RCV_TIMEOUT,0,sizeof(message),port,2000,0));check(message.h.msgh_id==first);
 check(!notify_cancel(first));
 mach_port_type_t type=0;kern_return_t e=mach_port_type(mach_task_self(),port,&type);check(e==KERN_INVALID_NAME || !(type&MACH_PORT_TYPE_RECEIVE));
 printf("NOTIFY_CROSS_PROCESS_MACH_DELIVERY_OK checks=%u\n",checks);return 0;
}
