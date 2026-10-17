#include <sys/attr.h>
#include <sys/stat.h>
#include <sys/vnode.h>
#include <dlfcn.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
typedef int (*Get)(const char *,struct attrlist *,void *,size_t,unsigned long);
static uint32_t word(const unsigned char *p) { uint32_t v;memcpy(&v,p,4);return v; }
static void check(Get get,const char *path,unsigned long options,unsigned expected_type,unsigned expected_links) {
    struct attrlist list={.bitmapcount=ATTR_BIT_MAP_COUNT,.commonattr=ATTR_CMN_OBJTYPE|ATTR_CMN_ACCESSMASK|ATTR_CMN_FULLPATH,.fileattr=ATTR_FILE_LINKCOUNT};
    unsigned char output[PATH_MAX+64];memset(output,0xcc,sizeof(output));
    assert(!get(path,&list,output,sizeof(output),options));
    struct stat st;assert(!(options&FSOPT_NOFOLLOW?lstat(path,&st):stat(path,&st)));
    assert(word(output+4)==expected_type && word(output+8)==st.st_mode);
    attrreference_t ref;memcpy(&ref,output+12,sizeof(ref));
    unsigned fixed=expected_type==VDIR?20:24;
    assert(ref.attr_dataoffset==(int32_t)(fixed-12));
    const char *name=(const char *)output+12+ref.attr_dataoffset;
    assert(name[ref.attr_length-1]==0 && strlen(name)+1==ref.attr_length);
    if(!(options&FSOPT_NOFOLLOW) || expected_type!=VLNK) {
        char canonical[PATH_MAX];assert(realpath(path,canonical));assert(!strcmp(name,canonical));
    } else { assert(strstr(name,"/link") && expected_type==VLNK); }
    if(expected_type!=VDIR)assert(word(output+20)==expected_links);
    unsigned needed=fixed+((ref.attr_length+3)&~3u);assert(word(output)==needed);
    for(unsigned i=needed;i<sizeof(output);i++)assert(output[i]==0xcc);
    for(unsigned size=1;size<=needed+8;size++)for(unsigned report=0;report<2;report++) {
        unsigned char guarded[PATH_MAX+80];memset(guarded,0xa5,sizeof(guarded));
        assert(!get(path,&list,guarded+8,size,options|(report?FSOPT_REPORT_FULLSIZE:0)));
        for(unsigned i=0;i<8;i++)assert(guarded[i]==0xa5);
        unsigned copied=size<needed?size:needed;
        for(unsigned i=copied;i<sizeof(guarded)-8;i++)assert(guarded[8+i]==0xa5);
        unsigned char expected[PATH_MAX+64];memcpy(expected,output,needed);
        uint32_t length=report?needed:copied;memcpy(expected,&length,4);
        assert(!memcmp(guarded+8,expected,copied));
    }
    // Individual fields have their documented 32-bit layout and do not write
    // beyond the length of their own result.
    list.commonattr=ATTR_CMN_OBJTYPE;list.fileattr=0;
    assert(!get(path,&list,output,sizeof(output),options) && word(output)==8 && word(output+4)==expected_type);
    list.commonattr=ATTR_CMN_ACCESSMASK;
    assert(!get(path,&list,output,sizeof(output),options) && word(output)==8 && word(output+4)==st.st_mode);
    list.commonattr=0;list.fileattr=ATTR_FILE_LINKCOUNT;
    assert(!get(path,&list,output,sizeof(output),options));
    if(expected_type==VDIR)assert(word(output)==4);
    else assert(word(output)==8 && word(output+4)==expected_links);
}
int main(int argc,char **argv) {
    assert(argc==2);void *h=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);if(!h){fputs(dlerror(),stderr);return 1;}
    Get get=(Get)dlsym(h,"getattrlist");assert(get);
    Dl_info owner;assert(dladdr((void *)get,&owner));assert(strstr(owner.dli_fname,"libDarlingFoundationSystem.dylib"));
    char pattern[]="/tmp/linuxcode-file-attrs-XXXXXX";char *dir=mkdtemp(pattern);assert(dir);
    char file[PATH_MAX],alias[PATH_MAX],symlink_path[PATH_MAX],missing[PATH_MAX];
    snprintf(file,sizeof(file),"%s/中文.txt",dir);snprintf(alias,sizeof(alias),"%s/hardlink",dir);
    snprintf(symlink_path,sizeof(symlink_path),"%s/link",dir);snprintf(missing,sizeof(missing),"%s/missing",dir);
    int fd=open(file,O_CREAT|O_EXCL|O_RDWR,0640);assert(fd>=0 && !fchmod(fd,0640));assert(write(fd,"abc",3)==3);assert(!close(fd));
    check(get,file,0,VREG,1);assert(!link(file,alias));check(get,file,0,VREG,2);check(get,alias,FSOPT_NOFOLLOW,VREG,2);
    assert(!symlink(file,symlink_path));check(get,symlink_path,0,VREG,2);check(get,symlink_path,FSOPT_NOFOLLOW,VLNK,1);
    check(get,dir,0,VDIR,0);
    struct attrlist list={.bitmapcount=ATTR_BIT_MAP_COUNT,.commonattr=ATTR_CMN_OBJTYPE|ATTR_CMN_ACCESSMASK|ATTR_CMN_FULLPATH,.fileattr=ATTR_FILE_LINKCOUNT};
    unsigned char buffer[128];memset(buffer,0x37,sizeof(buffer));
    errno=0;assert(get(missing,&list,buffer,sizeof(buffer),FSOPT_NOFOLLOW)==-1 && errno==ENOENT);
    for(unsigned i=0;i<sizeof(buffer);i++)assert(buffer[i]==0x37);
    errno=0;assert(get(file,&list,buffer,0,0)==-1 && errno==EINVAL);
    list.bitmapcount=4;assert(get(file,&list,buffer,sizeof(buffer),0)==-1 && errno==EINVAL);list.bitmapcount=5;
    list.reserved=1;assert(get(file,&list,buffer,sizeof(buffer),0)==-1 && errno==EINVAL);list.reserved=0;
    // Requests outside this extension retain actual backend failure behavior.
    list.commonattr=ATTR_CMN_USERACCESS;list.fileattr=0;errno=0;
    int old=getattrlist(file,&list,buffer,sizeof(buffer),0),old_errno=errno;errno=0;
    assert(get(file,&list,buffer,sizeof(buffer),0)==old && errno==old_errno && old==-1);
    assert(!unlink(symlink_path) && !unlink(alias) && !unlink(file) && !rmdir(dir));
    puts("FOUNDATION_FILE_ATTRS_REAL_MODE_TYPE_LINKS_UTF8_SYMLINKS_TRUNCATION_AND_ERRORS_OK");return 0;
}
