#include <sys/attr.h>
#include <sys/stat.h>
#include <sys/vnode.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static unsigned checks;
#define CHECK(x) do { checks++; if (!(x)) { fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#x); exit(2); } } while(0)
static int inspect(const char *path, const char *expected_name, const char *expected_path, int baseline) {
    struct attrlist attrs = {0};
    attrs.bitmapcount = ATTR_BIT_MAP_COUNT;
    attrs.commonattr = ATTR_CMN_NAME | ATTR_CMN_OBJTYPE | ATTR_CMN_FULLPATH;
    struct __attribute__((packed,aligned(4))) {
        uint32_t length; attrreference_t name; fsobj_type_t type;
        attrreference_t fullpath; char data[4096];
    } result;
    for (int method=0; method<2; method++) {
        memset(&result,0,sizeof result);
        int fd=open(path,O_RDONLY); CHECK(fd>=0);
        int rv=method ? fgetattrlist(fd,&attrs,&result,sizeof result,0) : getattrlist(path,&attrs,&result,sizeof result,0);
        close(fd); CHECK(rv==0); CHECK(result.type==VDIR);
        const char *name=(char*)&result.name+result.name.attr_dataoffset;
        const char *fullpath=(char*)&result.fullpath+result.fullpath.attr_dataoffset;
        printf("METADATA_ROOT_NAME method=%d path=%s name=%s fullpath=%s\n",method,path,name,fullpath);
        if (baseline && strcmp(name,expected_name)) return 1;
        CHECK(!strcmp(name,expected_name)); CHECK(!strcmp(fullpath,expected_path));
    }
    return 0;
}
int main(int argc,char **argv) {
    int baseline=argc>1 && !strcmp(argv[1],"baseline");
    if(inspect("/Volumes/SystemRoot","SystemRoot","/Volumes/SystemRoot",baseline)) {
        puts("BASELINE_VIRTUAL_ROOT_BASENAME_IS_ENTIRE_PATH"); return 2;
    }
    inspect("/Volumes/SystemRoot///","SystemRoot","/Volumes/SystemRoot",0);
    char root[]="/private/tmp/metadata-root-name.XXXXXX"; CHECK(mkdtemp(root)!=NULL);
    char path[1024]; snprintf(path,sizeof path,"%s/child with spaces",root); CHECK(!mkdir(path,0700));
    inspect(path,"child with spaces",path,0);
    char alias[1024];snprintf(alias,sizeof alias,"/tmp%s",path+strlen("/private/tmp"));
    inspect(alias,"child with spaces",path,0);
    char trailing[1030];snprintf(trailing,sizeof trailing,"%s///",path);inspect(trailing,"child with spaces",path,0);
    CHECK(!rmdir(path)); CHECK(!rmdir(root));
    printf("METADATA_VIRTUAL_ROOT_NAMES_PATH_FD_AND_TRAILING_SLASH_OK checks=%u\n",checks);
    return 0;
}
