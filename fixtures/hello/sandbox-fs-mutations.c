#include <sys/stat.h>
#include <sys/types.h>
#include <fcntl.h>
#include <unistd.h>
#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
static unsigned checks;
static char root[1024];
static int capture;
#define CHECK(x) do {checks++;if (!(x)) {fprintf(stderr,"FAIL line=%d expression=%s errno=%d\n",__LINE__,#x,errno);exit(1);}} while (0)
static void path(char *out,const char *name) {CHECK(snprintf(out,2048,"%s/%s",root,name)<2048);}
static void control(const char *value) {
    if (!capture) return;
    int fd=open("/Volumes/SystemRoot/workspace/runtime/sandbox-fs-query-enable",O_WRONLY|O_TRUNC);
    CHECK(fd>=0 && write(fd,value,1)==1 && close(fd)==0);
}
static void file(const char *name,const char *contents) {
    char p[2048];path(p,name);int fd=open(p,O_CREAT|O_WRONLY|O_TRUNC,0600);
    CHECK(fd>=0 && write(fd,contents,strlen(contents))==(ssize_t)strlen(contents) && close(fd)==0);
}
static void contents(const char *name,const char *expected) {
    char p[2048],data[64]={0};path(p,name);int fd=open(p,O_RDONLY);CHECK(fd>=0);
    CHECK(read(fd,data,sizeof data)==(ssize_t)strlen(expected) && !strcmp(data,expected));CHECK(close(fd)==0);
}
static int exists(const char *name) {char p[2048];path(p,name);struct stat s;return lstat(p,&s)==0;}
static void expected(int status,int error) {if (error) CHECK(status==-1 && errno==error);else CHECK(status==0);}
static unsigned descriptors(void) {unsigned result=0;for (int i=0;i<128;i++) if (fcntl(i,F_GETFD)!=-1) result++;return result;}
static void cleanup(const char *base) {
    DIR *d=opendir(base);CHECK(d);struct dirent *entry;
    while ((entry=readdir(d))) {
        if (!strcmp(entry->d_name,".") || !strcmp(entry->d_name,"..")) continue;
        char p[4096];CHECK(snprintf(p,sizeof p,"%s/%s",base,entry->d_name)<sizeof p);struct stat st;CHECK(lstat(p,&st)==0);
        if (S_ISDIR(st.st_mode)) cleanup(p);else CHECK(unlink(p)==0);
    }
    CHECK(closedir(d)==0 && rmdir(base)==0);
}
int main(int argc,char **argv) {
    setbuf(stdout,NULL);CHECK(argc==2);capture=!strcmp(argv[1],"capture");
    strcpy(root,"/tmp/linuxcode-sandbox-fs-XXXXXX");CHECK(mkdtemp(root));
    char canonical[1024];CHECK(realpath(root,canonical));strcpy(root,canonical);
    printf("SANDBOX_FS_ROOT %s capture=%d\n",root,capture);
    int directory=open(root,O_RDONLY|O_DIRECTORY);CHECK(directory>=0);
    control("1");unsigned initial=descriptors();
    char a[2048],b[2048];path(a,"allowed-dir");CHECK(mkdir(a,0700)==0 && exists("allowed-dir"));
    CHECK(mkdirat(directory,"at-dir",0700)==0 && exists("at-dir"));
    CHECK(chdir(root)==0 && mkdir("relative-dir",0700)==0 && chdir("/")==0);
    path(a,"real-parent");CHECK(mkdir(a,0700)==0);path(b,"alias");CHECK(symlink("real-parent",b)==0);
    path(a,"alias/deny-create-alias");errno=0;expected(mkdir(a,0700),capture?EPERM:0);
    CHECK(exists("real-parent/deny-create-alias")==!capture);
    const char *names[]={"deny-create","query-error-create","transport-error-create"};
    const int errors[]={EPERM,EIO,EAGAIN};
    for (unsigned i=0;i<3;i++) {path(a,names[i]);errno=0;expected(mkdir(a,0700),capture?errors[i]:0);CHECK(exists(names[i])==!capture);}
    file("deny-unlink-file","untouched");path(a,"deny-unlink-file");errno=0;expected(unlink(a),capture?EPERM:0);
    if (capture) contents("deny-unlink-file","untouched");else CHECK(!exists("deny-unlink-file"));
    path(a,"deny-unlink-dir");CHECK(mkdir(a,0700)==0);errno=0;expected(rmdir(a),capture?EPERM:0);CHECK(exists("deny-unlink-dir")==capture);
    file("at-unlink","gone");CHECK(unlinkat(directory,"at-unlink",0)==0 && !exists("at-unlink"));
    file("rename-source","moved");CHECK(renameat(directory,"rename-source",directory,"rename-target")==0);
    CHECK(!exists("rename-source"));contents("rename-target","moved");
    file("replace-source","replacement");file("replace-target","original");
    CHECK(renameat(directory,"replace-source",directory,"replace-target")==0);contents("replace-target","replacement");
    const char *sources[]={"deny-unlink-source","create-source","overwrite-source","error-source"};
    const char *targets[]={"unlink-target","deny-create-target","deny-unlink-target","query-error-target"};
    for (unsigned i=0;i<4;i++) {
        file(sources[i],"source");file(targets[i],"destination");path(a,sources[i]);path(b,targets[i]);
        errno=0;expected(rename(a,b),capture?(i==3?EIO:EPERM):0);
        if (capture) {contents(sources[i],"source");contents(targets[i],"destination");}
        else {CHECK(!exists(sources[i]));contents(targets[i],"source");}
    }
    for (unsigned i=0;i<32;i++) {
        char name[64];snprintf(name,sizeof name,"deny-create-repeat-%u",i);errno=0;
        expected(mkdirat(directory,name,0700),capture?EPERM:0);
    }
    errno=0;CHECK(mkdir((const char *)1,0700)==-1 && errno==EFAULT);
    errno=0;CHECK(unlinkat(directory,(const char *)1,0)==-1 && errno==EFAULT);
    path(a,"valid-target");errno=0;CHECK(rename((const char *)1,a)==-1 && errno==EFAULT);
    char long_name[4097];memset(long_name,'x',sizeof long_name-1);long_name[sizeof long_name-1]=0;
    errno=0;CHECK(mkdir(long_name,0700)==-1 && errno==ENAMETOOLONG);
    CHECK(descriptors()==initial);
    if (capture) {
        path(a,"parentA");path(b,"parentB");CHECK(mkdir(a,0700)==0 && mkdir(b,0700)==0);
        struct stat original,renamed;CHECK(stat(a,&original)==0);
        path(a,"parentA/swap-parent");CHECK(mkdir(a,0700)==0);
        CHECK(exists("savedA/swap-parent") && !exists("parentB/swap-parent"));
        path(a,"savedA");CHECK(stat(a,&renamed)==0 && original.st_ino==renamed.st_ino && original.st_dev==renamed.st_dev);
        puts("SANDBOX_FS_PINNED_PARENT_SURVIVES_PATH_REPLACEMENT_OK");
    }
    CHECK(descriptors()==initial);control("0");CHECK(close(directory)==0);cleanup(root);
    printf("SANDBOX_FS_MUTATIONS_NO_SIDE_EFFECTS_OR_FD_LEAKS_OK checks=%u capture=%d\n",checks,capture);return 0;
}
