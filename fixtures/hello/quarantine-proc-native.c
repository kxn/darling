#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
#include <unistd.h>
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"FAIL line=%d %s errno=%d\n",__LINE__,#x,errno);exit(1);}}while(0)
typedef void *object;
int main(void){
    setbuf(stdout,NULL);
    void *base=dlopen("/usr/lib/system/libquarantine.dylib",RTLD_LAZY|RTLD_LOCAL);CHECK(base);
    void *native=dlopen("/usr/lib/libDarlingNativeQuarantine.dylib",RTLD_LAZY|RTLD_LOCAL);CHECK(native);
    object(*alloc)(void)=dlsym(base,"_qtn_proc_alloc");object(*clone)(object)=dlsym(base,"_qtn_proc_clone");
    void(*release)(object)=dlsym(base,"_qtn_proc_free");void(*init)(object)=dlsym(base,"_qtn_proc_init");
    int(*flags)(object,unsigned)=dlsym(base,"_qtn_proc_set_flags");unsigned(*get_flags)(object)=dlsym(base,"_qtn_proc_get_flags");
    int(*set_id)(object,const char*)=dlsym(base,"_qtn_proc_set_identifier");const char*(*get_id)(object)=dlsym(base,"_qtn_proc_get_identifier");
    int(*set_data)(object,const void*,size_t)=dlsym(base,"_qtn_proc_set_metadata");size_t(*data_size)(object)=dlsym(base,"_qtn_proc_get_metadata_size");const void*(*get_data)(object)=dlsym(base,"_qtn_proc_get_metadata");
    int(*apply)(object)=dlsym(base,"_qtn_proc_apply_to_self");int(*init_self)(object)=dlsym(base,"_qtn_proc_init_with_self");
    CHECK(alloc&&clone&&release&&init&&flags&&get_flags&&set_id&&get_id&&set_data&&data_size&&get_data&&apply&&init_self);
    CHECK((void*)alloc==dlsym(native,"_qtn_proc_alloc"));CHECK((void*)apply==dlsym(native,"_qtn_proc_apply_to_self"));
    object p=alloc();CHECK(p);CHECK(get_flags(p)==0);init(p);CHECK(get_flags(p)==1);
    int(*set_pattern)(object,const char*)=dlsym(base,"_qtn_proc_set_path_exclusion_pattern");CHECK(set_pattern&&set_pattern(p,"")==0);
    CHECK(set_id(p,"org.darling.quarantine-proc-test")==0);CHECK(!strcmp(get_id(p),"org.darling.quarantine-proc-test"));
    for(unsigned n=0;n<=64;n++){
        uint8_t bytes[65];for(unsigned i=0;i<sizeof(bytes);i++)bytes[i]=i^n;
        CHECK(flags(p,n)==0&&get_flags(p)==n);CHECK(set_data(p,bytes,n)==0);CHECK(data_size(p)==n);CHECK(!memcmp(get_data(p),bytes,n));
        object copy=clone(p);CHECK(copy&&copy!=p);CHECK(get_flags(copy)==n&&data_size(copy)==n);CHECK(!memcmp(get_data(copy),bytes,n));
        CHECK(get_data(copy)!=get_data(p));CHECK(set_id(copy,"org.darling.independent-copy")==0);
        CHECK(strcmp(get_id(copy),get_id(p))!=0);CHECK(set_data(p,bytes,0)==0);CHECK(data_size(copy)==n);release(copy);
    }
    CHECK(flags(p,0x1fff)==0);CHECK(flags(p,0x2000)==EINVAL&&get_flags(p)==0x1fff);
    uint8_t bytes[65]={0};CHECK(set_data(p,bytes,sizeof(bytes))==ERANGE&&data_size(p)==0);
    char id[257];memset(id,'x',256);id[256]=0;CHECK(set_id(p,id)==ERANGE&&get_id(p)[0]==0);
    init(p);errno=0;int applied=apply(p);int apply_errno=errno;
    printf("NATIVE_QUARANTINE_REAL_APPLY_RESULT result=%d errno=%d\n",applied,apply_errno);
    CHECK(applied==ENOTSUP);
    errno=0;int loaded=init_self(p);printf("NATIVE_QUARANTINE_REAL_READ_RESULT result=%d errno=%d\n",loaded,errno);CHECK(loaded==ENOTSUP);
    release(p);dlclose(native);dlclose(base);
    printf("NATIVE_QUARANTINE_PROC_OBJECT_FLAGS_METADATA_CLONE_AND_UNSUPPORTED_POLICY_ERRORS_OK checks=%u\n",checks);
}
