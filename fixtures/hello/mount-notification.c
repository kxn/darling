#include <notify.h>
#include <mach/mach.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <fcntl.h>
extern int __linux_syscall(int,...);
#include <DiskArbitration/DiskArbitration.h>
#include <CoreFoundation/CoreFoundation.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
static unsigned checks,appeared;
#define check(c) do{++checks;if(!(c)){fprintf(stderr,"MOUNT_NOTIFY_FAIL line=%d check=%u\n",__LINE__,checks);exit(1);}}while(0)
static void event(mach_port_t port,int token){union{mach_msg_header_t h;char bytes[512];} msg;check(!mach_msg(&msg.h,MACH_RCV_MSG|MACH_RCV_TIMEOUT,0,sizeof(msg),port,20000,0));check(msg.h.msgh_id==token);}
static void disk_appeared(DADiskRef disk,void* context){(void)context;appeared++;printf("MOUNT_DA_APPEARED bsd=%s\n",DADiskGetBSDName(disk));}
int main(void){setbuf(stdout,NULL);char path[128];snprintf(path,sizeof(path),"/private/tmp/LinuxMountProbe-%d",getpid());check(!mkdir(path,0755));
 struct statfs before,current;check(!statfs(path,&before));mach_port_t ports[3]={0};int tokens[3]={0};const char* names[]={"com.apple.system.kernel.mount","com.apple.system.kernel.mountupdate","com.apple.system.kernel.unmount"};
 for(unsigned i=0;i<3;i++)check(!notify_register_mach_port(names[i],&ports[i],0,&tokens[i]));
 DASessionRef session=DASessionCreate(NULL);check(session);DARegisterDiskAppearedCallback(session,NULL,disk_appeared,NULL);DASessionScheduleWithRunLoop(session,CFRunLoopGetCurrent(),kCFRunLoopDefaultMode);
 usleep(700000);
 for(unsigned i=0;i<3;i++){union{mach_msg_header_t h;char bytes[512];} msg;while(!mach_msg(&msg.h,MACH_RCV_MSG|MACH_RCV_TIMEOUT,0,sizeof(msg),ports[i],0,0));}
 int directory=open(path,O_RDONLY);check(directory>=0);char fdpath[64],physical[4096];snprintf(fdpath,sizeof(fdpath),"/proc/self/fd/%d",directory);int n=__linux_syscall(89,fdpath,physical,sizeof(physical)-1);check(n>0);physical[n]=0;close(directory);
 printf("MOUNT_NOTIFY_READY path=%s linux_path=%s\n",path,physical);
 event(ports[0],tokens[0]);check(!statfs(path,&current));check(!strcmp(current.f_fstypename,"tmpfs"));check(current.f_flags&MNT_NOSUID);check(current.f_flags&MNT_NODEV);check(!(current.f_flags&MNT_UNION));check(memcmp(&before.f_fsid,&current.f_fsid,sizeof(before.f_fsid)));
 puts("MOUNT_NOTIFY_ADD");event(ports[1],tokens[1]);check(!statfs(path,&current));check(current.f_flags&MNT_RDONLY);puts("MOUNT_NOTIFY_UPDATE");
 event(ports[2],tokens[2]);check(!statfs(path,&current));check(!memcmp(&before.f_fsid,&current.f_fsid,sizeof(before.f_fsid)));puts("MOUNT_NOTIFY_REMOVE");
 for(unsigned i=0;i<8;i++)CFRunLoopRunInMode(kCFRunLoopDefaultMode,.25,false);
 const char* paths[]={"/","/Volumes/SystemRoot","/Volumes/SystemRoot/",NULL};
 for(unsigned i=0;paths[i];i++){
  struct statfs info;errno=0;int result=statfs(paths[i],&info);printf("MOUNT_PATH_STAT path=%s status=%d errno=%d mnton=%s\n",paths[i],result,errno,result?"?":info.f_mntonname);
  char resolved[4096];errno=0;char* actual=realpath(paths[i],resolved);printf("MOUNT_PATH_REAL path=%s actual=%s errno=%d\n",paths[i],actual?actual:"?",errno);
  CFURLRef url=CFURLCreateFromFileSystemRepresentation(NULL,(const UInt8*)paths[i],strlen(paths[i]),true);
  DADiskRef disk=DADiskCreateFromVolumePath(NULL,session,url);CFDictionaryRef description=disk?DADiskCopyDescription(disk):NULL;
  printf("MOUNT_DA_VOLUME path=%s disk=%p description=%p\n",paths[i],disk,description);
  check(disk!=NULL);check(description!=NULL);
  if(description){CFShow(description);CFRelease(description);}if(disk)CFRelease(disk);CFRelease(url);
 }
 DASessionUnscheduleFromRunLoop(session,CFRunLoopGetCurrent(),kCFRunLoopDefaultMode);CFRelease(session);
 for(unsigned i=0;i<3;i++)check(!notify_cancel(tokens[i]));check(!rmdir(path));
 printf("NATIVE_REAL_LINUX_MOUNT_UPDATE_UNMOUNT_NOTIFICATIONS_OK checks=%u appeared=%u\n",checks,appeared);return 0;
}
