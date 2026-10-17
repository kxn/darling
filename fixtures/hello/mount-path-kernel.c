#include <sys/mount.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
extern int statfs_ext(const char *,struct statfs *,int);
extern int fstatfs_ext(int,struct statfs *,int);
static unsigned checks;
#define CHECK(c) do{checks++;if(!(c)){fprintf(stderr,"MOUNT_PATH_FAIL %d errno=%d: %s\n",__LINE__,errno,#c);exit(1);}}while(0)
static void check_path(const char *path,const char *expected){
 struct statfs a,b,again;struct stat st;CHECK(statfs(path,&a)==0);CHECK(stat(path,&st)==0);CHECK(a.f_fsid.val[0]==st.st_dev);
 int fd=open(path,O_RDONLY);CHECK(fd>=0);CHECK(fstatfs(fd,&b)==0);CHECK(!strcmp(a.f_mntonname,b.f_mntonname));CHECK(!strcmp(a.f_fstypename,b.f_fstypename));CHECK(!memcmp(&a.f_fsid,&b.f_fsid,sizeof(fsid_t)));
 CHECK(a.f_mntonname[0]=='/');CHECK(strncmp(a.f_mntonname,"/state/prefix",13));CHECK(statfs(a.f_mntonname,&again)==0);CHECK(!memcmp(&a.f_fsid,&again.f_fsid,sizeof(fsid_t)));CHECK(!strcmp(a.f_fstypename,again.f_fstypename));
 for(int flags=0;flags<=1;flags++){
  struct statfs extended;CHECK(statfs_ext(path,&extended,flags)==0);CHECK(!memcmp(&a.f_fsid,&extended.f_fsid,sizeof(fsid_t)));CHECK(!strcmp(a.f_mntonname,extended.f_mntonname));CHECK(!strcmp(a.f_fstypename,extended.f_fstypename));CHECK(extended.f_bsize==a.f_bsize);
  CHECK(fstatfs_ext(fd,&extended,flags)==0);CHECK(!memcmp(&a.f_fsid,&extended.f_fsid,sizeof(fsid_t)));CHECK(!strcmp(a.f_mntonname,extended.f_mntonname));
 }
 if(expected)CHECK(!strcmp(a.f_mntonname,expected));char physical[4096];CHECK(fcntl(fd,F_GETPATH,physical)==0&&physical[0]=='/');CHECK(close(fd)==0);
 printf("MOUNT_PATH_ROUNDTRIP %s -> %s (%s)\n",path,a.f_mntonname,a.f_fstypename);
}
int main(void){setbuf(stdout,NULL);
 check_path("/","/");check_path("/System/Library/CoreServices/CoreTypes.bundle","/");
 const char *base="/Volumes/SystemRoot/workspace/runtime/mount-fixture";char path[4096],expected[4096];
 snprintf(path,sizeof(path),"%s/space mount",base);check_path(path,path);
 snprintf(path,sizeof(path),"%s/mount-prefix",base);check_path(path,path);
 snprintf(path,sizeof(path),"%s/mount-prefix-two",base);check_path(path,"/Volumes/SystemRoot/workspace");
 struct statfs neighboring,prefix;CHECK(statfs(path,&neighboring)==0);snprintf(path,sizeof(path),"%s/mount-prefix",base);CHECK(statfs(path,&prefix)==0);CHECK(strcmp(neighboring.f_fstypename,prefix.f_fstypename));
 check_path("/Volumes/SystemRoot/state/prefix-mount-test-neighbor","/Volumes/SystemRoot/state/prefix-mount-test-neighbor");
 int fd=open("/Volumes/SystemRoot/state/prefix-mount-test-neighbor",O_RDONLY);CHECK(fd>=0);char fdpath[4096];CHECK(fcntl(fd,F_GETPATH,fdpath)==0);CHECK(!strcmp(fdpath,"/Volumes/SystemRoot/state/prefix-mount-test-neighbor"));CHECK(close(fd)==0);
 snprintf(path,sizeof(path),"%s/source/deleted-test",base);fd=open(path,O_CREAT|O_EXCL|O_RDWR,0600);CHECK(fd>=0);CHECK(unlink(path)==0);struct statfs deleted;CHECK(fstatfs(fd,&deleted)==0);CHECK(statfs(deleted.f_mntonname,&prefix)==0);CHECK(!memcmp(&deleted.f_fsid,&prefix.f_fsid,sizeof(fsid_t)));CHECK(close(fd)==0);
 snprintf(path,sizeof(path),"%s/source/no-read",base);CHECK(statfs(path,&prefix)==0);
 int count=getfsstat(NULL,0,MNT_NOWAIT);CHECK(count>0);struct statfs *mounts=calloc(count+32,sizeof(*mounts));CHECK(mounts);int got=getfsstat(mounts,(count+32)*sizeof(*mounts),MNT_NOWAIT);CHECK(got==count);
 for(int i=0;i<got;i++){
  struct statfs resolved;CHECK(mounts[i].f_mntonname[0]=='/');CHECK(statfs(mounts[i].f_mntonname,&resolved)==0);CHECK(!memcmp(&mounts[i].f_fsid,&resolved.f_fsid,sizeof(fsid_t)));CHECK(!strcmp(mounts[i].f_fstypename,resolved.f_fstypename));
  for(int j=0;j<i;j++)CHECK(memcmp(&mounts[i].f_fsid,&mounts[j].f_fsid,sizeof(fsid_t)));
 }
 struct statfs invalid;memset(&invalid,0xa5,sizeof(invalid));errno=0;CHECK(statfs_ext(NULL,&invalid,0)==-1&&errno==EFAULT);CHECK(((unsigned char*)&invalid)[0]==0xa5);
 errno=0;CHECK(statfs_ext("/",NULL,0)==-1&&errno==EFAULT);errno=0;CHECK(fstatfs_ext(-1,NULL,0)==-1&&errno==EBADF);
 errno=0;CHECK(statfs_ext("/",&invalid,2)==-1&&errno==EINVAL);for(unsigned i=0;i<sizeof(invalid);i++)CHECK(((unsigned char*)&invalid)[i]==0);
 errno=0;CHECK(statfs_ext("/linuxcode-mount-missing",&invalid,1)==-1&&errno==ENOENT);
 free(mounts);printf("MOUNT_PATH_KERNEL_PASS checks=%u filesystems=%d\n",checks,got);return 0;
}
