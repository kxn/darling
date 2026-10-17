#include <mach/message.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <dlfcn.h>
#include <unistd.h>
typedef int(*pid_query)(int,const char*,int,...);
typedef int(*audit_query)(audit_token_t,const char*,int,...);
static unsigned checks,cases;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"FAIL %d %s\n",__LINE__,#x);exit(1);}}while(0)
static uint32_t small=0x89abcdef;static uint64_t large=0xfedcba9876543210ULL;
static const char payload[]="/tmp/中文-sandbox-query";
static audit_token_t token={{0xfedcba98,1,2,3,4,0xfffffffb,6,0x89abcdef}};
static int call(void *fn,int audit,const char *operation,unsigned filter) {
    unsigned kind=filter&0x81ffffffu;
#define INVOKE(...) (audit?((audit_query)fn)(token,operation,(int)filter,##__VA_ARGS__):((pid_query)fn)(-75,operation,(int)filter,##__VA_ARGS__))
    switch(kind){
        case 0:return INVOKE();
        case 10:case 14:case 16:case 18:return INVOKE((int)0x89abcdef);
        case 9:return INVOKE(payload,-89);
        case 11:return INVOKE(&small,&large);
        default:if(kind>=20)return INVOKE();return INVOKE(payload);
    }
#undef INVOKE
}
#ifdef CAPTURE_TEST
extern int capture_enabled,capture_return,capture_error,capture_calls,capture_has_operation;
extern uint64_t capture_decision,capture_words[20],capture_pair[2];extern char capture_operation[160];
#endif
int main(int argc,char **argv){
    CHECK(argc==2);void *native=dlopen(argv[1],RTLD_LAZY|RTLD_LOCAL);CHECK(native);
    void *source[2]={dlsym(RTLD_DEFAULT,"sandbox_check"),dlsym(RTLD_DEFAULT,"sandbox_check_by_audit_token")};
    void *original[2]={dlsym(native,"sandbox_check"),dlsym(native,"sandbox_check_by_audit_token")};
    CHECK(source[0]&&source[1]&&original[0]&&original[1]);
    const char *names[]={"SANDBOX_CHECK_NO_REPORT","SANDBOX_CHECK_CANONICAL","SANDBOX_CHECK_NOFOLLOW","SANDBOX_CHECK_NO_APPROVAL","SANDBOX_CHECK_ALLOW_APPROVAL","SANDBOX_CHECK_POSIX_READABLE","SANDBOX_CHECK_POSIX_WRITEABLE"};
    const uint32_t constants[]={0x40000000,0x20000000,0x10000000,0,0x08000000,0x04000000,0x02000000};
    for(unsigned i=0;i<7;i++){uint32_t *a=dlsym(RTLD_DEFAULT,names[i]),*b=dlsym(native,names[i]);CHECK(a&&b);CHECK(*a==constants[i]&&*a==*b);}
    Dl_info owner;CHECK(dladdr(source[0],&owner));CHECK(!strcmp(owner.dli_fname,"/usr/lib/system/libsystem_sandbox.dylib"));
    CHECK(dladdr(original[0],&owner));CHECK(!strcmp(owner.dli_fname,argv[1]));
#ifdef CAPTURE_TEST
    capture_enabled=1;
    for(unsigned audit=0;audit<2;audit++)for(unsigned flags=0;flags<64;flags++)for(unsigned kind=0;kind<20;kind++)for(unsigned outcome=0;outcome<5;outcome++){
        unsigned filter=kind;for(unsigned bit=0;bit<6;bit++)if(flags&(1u<<bit))filter|=1u<<(30-bit);
        capture_return=outcome==3?-1:outcome==4?1:0;capture_error=outcome==4?EIO:EACCES;capture_decision=outcome==0?0:outcome==1?1:UINT64_MAX;
        capture_calls=0;errno=EDOM;int a=call(source[audit],audit,"file-read-data",filter);int ae=errno;
        CHECK(capture_calls==1);uint64_t words[20],pair[2];memcpy(words,capture_words,sizeof(words));memcpy(pair,capture_pair,sizeof(pair));
        CHECK(capture_has_operation && !strcmp(capture_operation,"file-read-data"));
        CHECK(words[1]==(audit?(uint64_t)token.val[5]:(uint64_t)(int64_t)-75));CHECK(words[6]==(audit?token.val[7]:0));
        uint64_t expected_flags=audit?0x40000000:0;const unsigned bits[]={1,2,8,16,32,64};for(unsigned j=0;j<6;j++)if(flags&(1u<<j))expected_flags|=bits[j];CHECK(words[5]==expected_flags);
        for(unsigned j=7;j<20;j++)CHECK(words[j]==0);
        capture_calls=0;errno=EDOM;int b=call(original[audit],audit,"file-read-data",filter);int be=errno;
        CHECK(capture_calls==1);CHECK(a==b&&ae==be);CHECK(!memcmp(words,capture_words,sizeof(words)));CHECK(!memcmp(pair,capture_pair,sizeof(pair)));cases++;
    }
    for(unsigned audit=0;audit<2;audit++)for(unsigned i=0;i<2;i++){
        const char *op=i?NULL:"iokit-open";capture_return=0;capture_decision=0;capture_calls=0;
        CHECK(call(source[audit],audit,op,0)==0);CHECK(capture_calls==1);CHECK(capture_has_operation==!i);if(!i)CHECK(!strcmp(capture_operation,"iokit-open-user-client"));
        CHECK(call(original[audit],audit,op,0)==0);CHECK(capture_calls==2);CHECK(capture_has_operation==!i);if(!i)CHECK(!strcmp(capture_operation,"iokit-open-user-client"));cases++;
    }
    const unsigned invalid[]={20,255,0x01000000,0x80000000,0xffffffff};
    for(unsigned audit=0;audit<2;audit++)for(unsigned i=0;i<5;i++){
        capture_calls=0;errno=0;CHECK(call(source[audit],audit,"file-read-data",invalid[i])==-1&&errno==EINVAL);CHECK(capture_calls==0);
        errno=0;CHECK(call(original[audit],audit,"file-read-data",invalid[i])==-1&&errno==EINVAL);CHECK(capture_calls==0);cases++;
    }
    capture_enabled=0;printf("SOURCE_SANDBOX_QUERY_NATIVE_ABI_FLAGS_FILTERS_DECISIONS_ERRORS_OK cases=%u checks=%u\n",cases,checks);
#else
    for(unsigned audit=0;audit<2;audit++)for(unsigned flags=0;flags<64;flags++)for(unsigned kind=0;kind<20;kind++){
        unsigned filter=kind;for(unsigned bit=0;bit<6;bit++)if(flags&(1u<<bit))filter|=1u<<(30-bit);
        errno=0;int a=call(source[audit],audit,"file-read-data",filter);int ae=errno;errno=0;int b=call(original[audit],audit,"file-read-data",filter);int be=errno;
        CHECK(a==b&&ae==be);CHECK(a==-1&&ae==ENOPOLICY);cases++;
    }
    printf("SOURCE_SANDBOX_REAL_MISSING_POLICY_ERRORS_OK cases=%u checks=%u\n",cases,checks);
#endif
    return 0;
}
