#include <sys/mount.h>
#include <sys/stat.h>
#include <dlfcn.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdint.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
typedef int (*ByPath)(const char *,struct statfs *,int);
typedef int (*ByFD)(int,struct statfs *,int);
static void compare(const struct statfs *actual,const struct statfs *expected) {
    if(actual->f_bsize!=expected->f_bsize || actual->f_iosize!=expected->f_iosize)
        fprintf(stderr,"STATFS_DIFF bsize=%u/%u iosize=%d/%d type=%u/%u mount=%s/%s\n",
            actual->f_bsize,expected->f_bsize,actual->f_iosize,expected->f_iosize,actual->f_type,expected->f_type,
            actual->f_mntonname,expected->f_mntonname);
    assert(actual->f_bsize==expected->f_bsize && actual->f_iosize==expected->f_iosize);
    assert(!memcmp(&actual->f_fsid,&expected->f_fsid,sizeof(actual->f_fsid)));
    assert(actual->f_owner==expected->f_owner && actual->f_type==expected->f_type);
    assert(actual->f_flags==expected->f_flags && actual->f_fssubtype==expected->f_fssubtype);
    assert(!strcmp(actual->f_fstypename,expected->f_fstypename));
    assert(!strcmp(actual->f_mntonname,expected->f_mntonname));
    assert(!strcmp(actual->f_mntfromname,expected->f_mntfromname));
    assert(actual->f_blocks>0 && actual->f_bfree<=actual->f_blocks);
}
int main(int argc,char **argv) {
    assert(argc==2);void *h=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);if(!h){fputs(dlerror(),stderr);return 1;}
    ByPath path=(ByPath)dlsym(h,"statfs_ext");ByFD fd=(ByFD)dlsym(h,"fstatfs_ext");assert(path && fd);
    const char *paths[]={"/tmp","/Volumes/SystemRoot/workspace","/usr/lib/system/libsystem_kernel.dylib"};
    struct { uint64_t before;struct statfs value;uint64_t after; } guarded;
    for(unsigned i=0;i<3;i++) {
        int file=open(paths[i],O_RDONLY);assert(file>=0);struct statfs normal={0};assert(!statfs(paths[i],&normal));
        for(unsigned flags=0;flags<2;flags++) {
            fprintf(stderr,"STATFS_CASE path=%s flags=%u\n",paths[i],flags);
            // The existing backend's path and fd implementations expose some
            // different mount details. Compare each wrapper with its own API.
            memset(&normal,0,sizeof(normal));assert(!statfs(paths[i],&normal));
            memset(&guarded,0xa5,sizeof(guarded));assert(!path(paths[i],&guarded.value,flags));compare(&guarded.value,&normal);
            assert(guarded.before==UINT64_C(0xa5a5a5a5a5a5a5a5) && guarded.after==guarded.before);
            memset(&normal,0,sizeof(normal));assert(!fstatfs(file,&normal));
            memset(&guarded,0xa5,sizeof(guarded));assert(!fd(file,&guarded.value,flags));compare(&guarded.value,&normal);
            assert(guarded.before==UINT64_C(0xa5a5a5a5a5a5a5a5) && guarded.after==guarded.before);
        }
        assert(!close(file));errno=0;assert(fd(file,&normal,0)==-1 && errno==EBADF);
    }
    struct statfs result;
    errno=0;assert(path(NULL,&result,0)==-1 && errno==EFAULT);
    errno=0;assert(path("/tmp",NULL,0)==-1 && errno==EFAULT);
    errno=0;assert(fd(-1,&result,0)==-1 && errno==EBADF);
    errno=0;assert(path("/tmp/linuxcode-statfs-missing-47163",&result,0)==-1 && errno==ENOENT);
    for(unsigned flags=2;flags<256;flags+=7) {
        memset(&result,0x77,sizeof(result));errno=0;
        assert(path("/tmp",&result,flags)==-1 && errno==EINVAL);
        for(unsigned i=0;i<sizeof(result);i++)assert(!((unsigned char *)&result)[i]);
    }
    puts("APPLE_STATFS_EXT_REAL_PATH_FD_NONBLOCK_FALLBACK_BOUNDS_AND_ERRORS_OK");return 0;
}
