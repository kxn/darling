// Selected getattrlist fields over the actual Darwin filesystem backend.
// Packing follows XNU vfs_attrlist.c; unsupported requests retain the old API.
#include <sys/attr.h>
#include <sys/stat.h>
#include <sys/vnode.h>
#include <dlfcn.h>
#include <pthread.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <errno.h>

typedef int (*getattr_fn)(const char *,struct attrlist *,void *,size_t,unsigned long);
static getattr_fn original;
static pthread_once_t once=PTHREAD_ONCE_INIT;
static void resolve_original(void) {
    void *handle=dlopen("/usr/lib/system/libsystem_kernel.dylib",RTLD_LAZY|RTLD_NOLOAD);
    if(!handle || !(original=(getattr_fn)dlsym(handle,"getattrlist")))abort();
    dlclose(handle);
}
static int failure(int code) { errno=code;return -1; }
static fsobj_type_t vnode_type(mode_t mode) {
    switch(mode&S_IFMT) {
        case S_IFREG:return VREG;case S_IFDIR:return VDIR;
        case S_IFBLK:return VBLK;case S_IFCHR:return VCHR;
        case S_IFLNK:return VLNK;case S_IFSOCK:return VSOCK;
        case S_IFIFO:return VFIFO;default:return VNON;
    }
}
static int canonical_path(const char *path,bool nofollow,const struct stat *info,char output[PATH_MAX]) {
    if(!nofollow || !S_ISLNK(info->st_mode))return realpath(path,output)?0:-1;
    char *copy=strdup(path);if(!copy)return -1;
    char *slash=strrchr(copy,'/'),*name=slash?slash+1:copy;
    char parent[PATH_MAX];
    if(slash) { *slash=0;if(!realpath(*copy?copy:"/",parent)){free(copy);return -1;} }
    else if(!realpath(".",parent)){free(copy);return -1;}
    size_t length=strlen(parent),tail=strlen(name);bool root=length==1 && *parent=='/';
    if(length+(!root)+tail+1>PATH_MAX){free(copy);return failure(ENAMETOOLONG);}
    memcpy(output,parent,length);if(!root)output[length++]='/';memcpy(output+length,name,tail+1);
    free(copy);return 0;
}
int getattrlist(const char *path,struct attrlist *attributes,void *buffer,size_t size,unsigned long options) {
    if(!path || !attributes || (!buffer && size))return failure(EFAULT);
    const attrgroup_t supported=ATTR_CMN_OBJTYPE|ATTR_CMN_ACCESSMASK|ATTR_CMN_FULLPATH;
    if((attributes->commonattr&~supported) || attributes->volattr || attributes->dirattr ||
       (attributes->fileattr&~ATTR_FILE_LINKCOUNT) || attributes->forkattr ||
       (options&~(FSOPT_NOFOLLOW|FSOPT_REPORT_FULLSIZE))) {
        pthread_once(&once,resolve_original);return original(path,attributes,buffer,size,options);
    }
    if(attributes->bitmapcount!=ATTR_BIT_MAP_COUNT || attributes->reserved || !size)return failure(EINVAL);
    struct stat info;
    if((options&FSOPT_NOFOLLOW?lstat(path,&info):stat(path,&info)))return -1;
    char fullpath[PATH_MAX];size_t path_size=0;
    if(attributes->commonattr&ATTR_CMN_FULLPATH) {
        if(canonical_path(path,options&FSOPT_NOFOLLOW,&info,fullpath))return -1;
        path_size=strlen(fullpath)+1;
    }
    unsigned char output[PATH_MAX+64]={0};size_t cursor=4,reference=0;
    if(attributes->commonattr&ATTR_CMN_OBJTYPE){uint32_t type=vnode_type(info.st_mode);memcpy(output+cursor,&type,4);cursor+=4;}
    if(attributes->commonattr&ATTR_CMN_ACCESSMASK){uint32_t mode=info.st_mode;memcpy(output+cursor,&mode,4);cursor+=4;}
    if(path_size){reference=cursor;cursor+=sizeof(attrreference_t);}
    // XNU ignores the file group for directory vnodes.
    if((attributes->fileattr&ATTR_FILE_LINKCOUNT) && !S_ISDIR(info.st_mode)) {
        uint32_t links=info.st_nlink;memcpy(output+cursor,&links,4);cursor+=4;
    }
    if(path_size) {
        attrreference_t ref={.attr_dataoffset=(int32_t)(cursor-reference),.attr_length=(uint32_t)path_size};
        memcpy(output+reference,&ref,sizeof(ref));memcpy(output+cursor,fullpath,path_size);
        cursor+=(path_size+3)&~(size_t)3;
    }
    size_t copied=size<cursor?size:cursor;
    uint32_t length=options&FSOPT_REPORT_FULLSIZE?cursor:copied;
    memcpy(output,&length,4);memcpy(buffer,output,copied);return 0;
}
