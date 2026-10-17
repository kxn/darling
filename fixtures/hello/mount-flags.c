#include <sys/mount.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
extern int __linux_syscall(int,...);
struct linux_fs {long type,bsize;unsigned long blocks,bfree,bavail,files,ffree,fsid;long namelen,frsize,flags,spare[4];};
static unsigned checks;
#define check(c) do{++checks;if(!(c)){fprintf(stderr,"MOUNT_FLAGS_FAIL line=%d check=%u\n",__LINE__,checks);exit(1);}}while(0)
int main(void){setbuf(stdout,NULL);
 const char* paths[]={"/","/Volumes/SystemRoot/","/tmp","/proc",NULL};
 for(unsigned i=0;paths[i];i++){
  int fd=open(paths[i],O_RDONLY);check(fd>=0);struct statfs a,b;struct linux_fs linux;
  check(!statfs(paths[i],&a));check(!fstatfs(fd,&b));check(!__linux_syscall(138,fd,&linux));
  unsigned expected=0;unsigned long f=linux.flags;
  if(f&1)expected|=MNT_RDONLY;if(f&2)expected|=MNT_NOSUID;if(f&4)expected|=MNT_NODEV;if(f&8)expected|=MNT_NOEXEC;if(f&16)expected|=MNT_SYNCHRONOUS;if(f&1024)expected|=MNT_NOATIME;
  unsigned mask=MNT_RDONLY|MNT_NOSUID|MNT_NODEV|MNT_NOEXEC|MNT_SYNCHRONOUS|MNT_NOATIME;
  check((a.f_flags&mask)==expected);check(a.f_flags==b.f_flags);check(!(a.f_flags&MNT_UNION));check(!(a.f_flags&MNT_QUARANTINE));
  check(!memcmp(&a.f_fsid,&b.f_fsid,sizeof(a.f_fsid)));
  size_t length=strlen(a.f_mntonname);check(length>0);check(length==1 || a.f_mntonname[length-1]!='/');
  if(!strcmp(a.f_mntonname,"/"))check(a.f_flags&MNT_ROOTFS);
  printf("MOUNT_FLAGS path=%s type=%s linux=0x%lx darwin=0x%x mnton=%s\n",paths[i],a.f_fstypename,linux.flags,a.f_flags,a.f_mntonname);close(fd);
 }
 struct statfs* volumes=NULL;int count=getmntinfo(&volumes,MNT_NOWAIT);check(count>0);
 int systemroot=0;
 for(int i=0;i<count;i++){check(!(volumes[i].f_flags&MNT_UNION));size_t length=strlen(volumes[i].f_mntonname);check(length>0);check(length==1 || volumes[i].f_mntonname[length-1]!='/');if(!strcmp(volumes[i].f_mntonname,"/"))check(volumes[i].f_flags&MNT_ROOTFS);if(!strcmp(volumes[i].f_mntonname,"/Volumes/SystemRoot"))systemroot++;}
 check(systemroot==1);
 printf("NATIVE_MOUNT_FLAGS_LINUX_TRANSLATION_OK checks=%u mounts=%d\n",checks,count);return 0;
}
