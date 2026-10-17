// Optional diagnostic interposition only; preserves actual results and errno.
#include <fcntl.h>
#include <unistd.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <sys/stat.h>
#include <sys/attr.h>
#define INTERPOSE(replacement, original) \
    __attribute__((used,section("__DATA,__interpose"))) static const struct {const void *to,*from;} \
    interpose_##original={(const void *)replacement,(const void *)original}
static int trace_open(const char *path,int flags,...) {
    mode_t mode=0;if(flags&O_CREAT){va_list args;va_start(args,flags);mode=va_arg(args,int);va_end(args);}
    int result=open(path,flags,mode),saved=errno;
    fprintf(stderr,"FILE_TRACE open(%s,%#x,%#o)=%d errno=%d\n",path,flags,mode,result,saved);
    errno=saved;return result;
}
static int trace_openat(int fd,const char *path,int flags,...) {
    mode_t mode=0;if(flags&O_CREAT){va_list args;va_start(args,flags);mode=va_arg(args,int);va_end(args);}
    int result=openat(fd,path,flags,mode),saved=errno;
    fprintf(stderr,"FILE_TRACE openat(%d,%s,%#x,%#o)=%d errno=%d\n",fd,path,flags,mode,result,saved);
    errno=saved;return result;
}
static int trace_mkstemp(char *path) {
    int result=mkstemp(path),saved=errno;
    fprintf(stderr,"FILE_TRACE mkstemp(%s)=%d errno=%d\n",path,result,saved);errno=saved;return result;
}
// x86_64 register-level forwarding preserves the third argument's bits. This
// debugging entry does not inspect memory arguments or synthesize flags.
static int trace_fcntl(int fd,int command,uintptr_t argument) {
    int result=fcntl(fd,command,argument),saved=errno;
    fprintf(stderr,"FILE_TRACE fcntl(%d,%d,%#lx)=%d errno=%d\n",fd,command,argument,result,saved);errno=saved;return result;
}
static int trace_rename(const char *from,const char *to) {
    int result=rename(from,to),saved=errno;
    fprintf(stderr,"FILE_TRACE rename(%s,%s)=%d errno=%d\n",from,to,result,saved);errno=saved;return result;
}
static int trace_fchmod(int fd,mode_t mode) {
    int result=fchmod(fd,mode),saved=errno;
    fprintf(stderr,"FILE_TRACE fchmod(%d,%#o)=%d errno=%d\n",fd,mode,result,saved);errno=saved;return result;
}
INTERPOSE(trace_open,open);
INTERPOSE(trace_openat,openat);
INTERPOSE(trace_mkstemp,mkstemp);
INTERPOSE(trace_fcntl,fcntl);
INTERPOSE(trace_rename,rename);
INTERPOSE(trace_fchmod,fchmod);
static int trace_getattrlist(const char *path,struct attrlist *attributes,void *buffer,size_t size,unsigned long flags) {
    int result=getattrlist(path,attributes,buffer,size,flags),saved=errno;
    fprintf(stderr,"FILE_TRACE getattrlist(%s,common=%#x,vol=%#x,dir=%#x,file=%#x,size=%lu,flags=%#lx)=%d errno=%d\n",
        path,attributes->commonattr,attributes->volattr,attributes->dirattr,attributes->fileattr,size,flags,result,saved);
    errno=saved;return result;
}
INTERPOSE(trace_getattrlist,getattrlist);
extern int sandbox_check(pid_t,const char *,int,...);
static int trace_sandbox(pid_t pid,const char *operation,int filter,uintptr_t a,uintptr_t b,uintptr_t c) {
    int result=sandbox_check(pid,operation,filter,a,b,c),saved=errno;
    fprintf(stderr,"FILE_TRACE sandbox_check(%d,%s,%#x,%#lx)=%d errno=%d\n",pid,operation?operation:"NULL",filter,a,result,saved);
    errno=saved;return result;
}
INTERPOSE(trace_sandbox,sandbox_check);
