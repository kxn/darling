#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>
#include <dlfcn.h>
#include <pthread.h>
static unsigned checks;
#define CHECK(x) do { checks++; if(!(x)){fprintf(stderr,"DIRECTORY_CHECK_FAILED line=%u expr=%s errno=%d\n",__LINE__,#x,errno);exit(1);} }while(0)
extern char *_dirhelper(int,char *,size_t);
extern int _set_user_dir_suffix(const char *);
static void directory(const char *path){struct stat st;CHECK(stat(path,&st)==0);CHECK(S_ISDIR(st.st_mode));}
int main(void){
 setbuf(stdout,NULL);
 Dl_info owner={0};CHECK(dladdr((void *)_dirhelper,&owner));printf("DIRECTORY_HELPER_OWNER %s\n",owner.dli_fname);
 char scratch[]="/tmp/coreservices-directories.XXXXXX";CHECK(mkdtemp(scratch));
 char home[1024],temp[1024],path[1024],expect[1024],file[1024];
 snprintf(home,sizeof home,"%s/home",scratch);snprintf(temp,sizeof temp,"%s/temp",scratch);
 CHECK(mkdir(home,0700)==0);CHECK(mkdir(temp,0700)==0);CHECK(setenv("HOME",home,1)==0);CHECK(setenv("TMPDIR",temp,1)==0);
 char suffix[64]="org.example.darling.directory-test";CHECK(_set_user_dir_suffix(suffix));
 CHECK(confstr(_CS_DARWIN_USER_CACHE_DIR,path,sizeof path)>0);
 snprintf(expect,sizeof expect,"%s/.cache/org.example.darling.directory-test/",home);CHECK(strcmp(path,expect)==0);directory(path);
 struct stat st;CHECK(stat(path,&st)==0);CHECK((st.st_mode&0777)==0700);
 strcpy(suffix,"changed-after-call");CHECK(_dirhelper(2,path,sizeof path)==path);CHECK(strcmp(path,expect)==0);
 CHECK(confstr(_CS_DARWIN_USER_TEMP_DIR,path,sizeof path)>0);snprintf(expect,sizeof expect,"%s/org.example.darling.directory-test/",temp);CHECK(strcmp(path,expect)==0);directory(path);
 CHECK(confstr(_CS_DARWIN_USER_DIR,path,sizeof path)>0);snprintf(expect,sizeof expect,"%s/org.example.darling.directory-test/",home);CHECK(strcmp(path,expect)==0);directory(path);
 for(int i=0;i<32;i++){CHECK(_dirhelper(2,path,sizeof path)==path);directory(path);}
 char small[8];memset(small,0x5a,sizeof small);errno=0;CHECK(!_dirhelper(2,small,4));CHECK(errno==ENAMETOOLONG);CHECK(small[4]==0x5a);
 errno=0;CHECK(!_dirhelper(-1,path,sizeof path));CHECK(errno==EINVAL);errno=0;CHECK(!_dirhelper(3,path,sizeof path));CHECK(errno==EINVAL);
 errno=0;CHECK(!_dirhelper(0,NULL,sizeof path));CHECK(errno==EINVAL);errno=0;CHECK(!_dirhelper(0,path,0));CHECK(errno==EINVAL);
 snprintf(file,sizeof file,"%s/file",scratch);int fd=open(file,O_WRONLY|O_CREAT|O_EXCL,0600);CHECK(fd>=0);CHECK(close(fd)==0);
 CHECK(setenv("HOME",file,1)==0);errno=0;CHECK(!_dirhelper(2,path,sizeof path));CHECK(errno==ENOTDIR);CHECK(setenv("HOME",home,1)==0);
 CHECK(_set_user_dir_suffix("collision"));snprintf(file,sizeof file,"%s/.cache/collision",home);fd=open(file,O_WRONLY|O_CREAT|O_EXCL,0600);CHECK(fd>=0);CHECK(close(fd)==0);errno=0;CHECK(!_dirhelper(2,path,sizeof path));CHECK(errno==ENOTDIR);CHECK(unlink(file)==0);
 CHECK(_set_user_dir_suffix(NULL));CHECK(_dirhelper(2,path,sizeof path)==path);snprintf(expect,sizeof expect,"%s/.cache/",home);CHECK(strcmp(path,expect)==0);directory(path);
 char fresh[1024];snprintf(fresh,sizeof fresh,"%s/fresh-home",scratch);CHECK(setenv("HOME",fresh,1)==0);CHECK(_set_user_dir_suffix("fresh-service"));CHECK(_dirhelper(2,path,sizeof path)==path);directory(fresh);directory(path);CHECK(setenv("HOME",home,1)==0);CHECK(_set_user_dir_suffix(NULL));
 printf("DIRECTORY_HELPER_FUNCTIONAL_OK checks=%u\n",checks);return 0;
}
