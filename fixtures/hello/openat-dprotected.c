#include <sys/types.h>
#include <sys/stat.h>
#include <sys/fcntl.h>
#include <dlfcn.h>
#include <unistd.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
typedef int (*Open)(int,const char *,int,int,int,...);
int main(int argc,char **argv) {
    assert(argc==3);
    void *library=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);
    if (!library) { fprintf(stderr,"%s\n",dlerror());return 1; }
    Open protectedOpen=(Open)dlsym(library,"openat_dprotected_np");assert(protectedOpen);
    Dl_info owner;assert(dladdr((void *)protectedOpen,&owner));
    char *actual=realpath(owner.dli_fname,NULL),*expected=realpath(argv[1],NULL);
    assert(actual && expected && !strcmp(actual,expected));free(actual);free(expected);
    assert(!mkdir(argv[2],0700));int directory=open(argv[2],O_RDONLY|O_DIRECTORY);assert(directory>=0);
    mode_t prior=umask(0077);
    int file=protectedOpen(directory,"one",O_CREAT|O_EXCL|O_RDWR|O_CLOEXEC,-1,0,0666);assert(file>=0);
    struct stat info;assert(!fstat(file,&info) && (info.st_mode&0777)==0600);
    assert(fcntl(file,F_GETFD)&FD_CLOEXEC);
    const char bytes[]={0,'a',0,'z',(char)0xff};assert(write(file,bytes,sizeof(bytes))==sizeof(bytes));assert(!close(file));
    errno=0;assert(protectedOpen(directory,"one",O_CREAT|O_EXCL|O_RDWR,-1,0,0600)==-1 && errno==EEXIST);
    // XNU applies the protection-class argument only when O_CREAT is set.
    file=protectedOpen(directory,"one",O_RDONLY,12345,0);assert(file>=0);
    char copy[sizeof(bytes)];assert(read(file,copy,sizeof(copy))==sizeof(copy) && !memcmp(copy,bytes,sizeof(bytes)));assert(!close(file));
    file=protectedOpen(directory,"one",O_WRONLY|O_APPEND,-1,0);assert(file>=0);assert(write(file,"!",1)==1);assert(!close(file));
    file=protectedOpen(directory,"one",O_WRONLY|O_TRUNC,-1,0);assert(file>=0);assert(!fstat(file,&info) && info.st_size==0);assert(!close(file));
    for (int protection=0;protection<=6;protection++) {
        errno=0;assert(protectedOpen(directory,"protected",O_CREAT|O_WRONLY,protection,0,0600)==-1 && errno==ENOTSUP);
        assert(fstatat(directory,"protected",&info,0)==-1 && errno==ENOENT);
    }
    for (unsigned flag=1;flag<=0x80;flag<<=1) {
        errno=0;assert(protectedOpen(directory,"one",O_RDONLY,-1,flag)==-1 && errno==ENOTSUP);
    }
    errno=0;assert(protectedOpen(directory,"one",O_WRONLY,-1,O_DP_GETRAWENCRYPTED)==-1 && errno==EINVAL);
    errno=0;assert(protectedOpen(-1,"one",O_RDONLY,-1,0)==-1 && errno==EBADF);
    errno=0;assert(protectedOpen(123456,"one",O_RDONLY,-1,0)==-1 && errno==EBADF);
    errno=0;assert(protectedOpen(directory,"missing",O_RDONLY,-1,0)==-1 && errno==ENOENT);
    // The existing Darling symlinkat implementation ignores its directory fd.
    // Build this fixture via an absolute pathname so this test measures the
    // new open API's nofollow behavior independently of that existing bug.
    char linkPath[4096];assert(snprintf(linkPath,sizeof(linkPath),"%s/link",argv[2])<(int)sizeof(linkPath));
    assert(!symlink("one",linkPath));
    errno=0;int nofollow=protectedOpen(directory,"link",O_RDONLY|O_NOFOLLOW,-1,0);
    if (nofollow!=-1 || errno!=ELOOP)fprintf(stderr,"nofollow result=%d errno=%d expected=%d\n",nofollow,errno,ELOOP);
    assert(nofollow==-1 && errno==ELOOP);
    file=protectedOpen(AT_FDCWD,argv[2],O_RDONLY|O_DIRECTORY,-1,0);assert(file>=0);assert(!close(file));
    file=protectedOpen(-1,argv[2],O_RDONLY|O_DIRECTORY,-1,0);assert(file>=0);assert(!close(file));
    assert(!unlinkat(directory,"link",0) && !unlinkat(directory,"one",0));
    assert(!close(directory));assert(!rmdir(argv[2]));umask(prior);
    puts("OPENAT_DEFAULT_ACTUAL_FILES_MODES_CONTENT_FLAGS_ERRORS_AND_PROTECTION_REJECTION_OK");
    return 0;
}
