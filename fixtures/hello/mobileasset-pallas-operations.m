#import <Foundation/Foundation.h>
#include <assert.h>
#include <dlfcn.h>
#include <mach/mach.h>
#include <pthread.h>
#include <servers/bootstrap.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>
#include <uuid/uuid.h>
#include <xpc/xpc.h>

extern int xpc_pipe_receive(mach_port_t, xpc_object_t*, uint64_t);
extern int xpc_pipe_routine_reply(xpc_object_t);
typedef int64_t (*EnabledGetter)(NSString*, bool*);
typedef int64_t (*EnabledSetter)(NSString*, BOOL);
typedef NSString* (*AudienceGetter)(NSString*);
typedef int64_t (*AudienceSetter)(NSString*, NSString*);
typedef int64_t (*UrlSetter)(NSURL*, NSString*);
typedef int64_t (*GlobalAudienceSetter)(NSString*);
typedef int64_t (*GlobalUrlSetter)(NSURL*);
static EnabledGetter getEnabled;
static EnabledSetter setEnabled;
static AudienceGetter getAudience, internalAudience;
static AudienceSetter setAudience, internalSetAudience;
static UrlSetter setUrl, internalSetUrl;
static GlobalAudienceSetter globalAudience;
static GlobalUrlSetter globalUrl, internalGlobalUrl;
static const int64_t wideError = -INT64_C(0x123456789);
static const char* service = "com.apple.mobileassetd.v2";
static const char* encodedUrl = "https://example.invalid/a%20b?x=1&y=%E4%B8%AD";
static int64_t statusFor(unsigned i) {
    if (i == 4 || i == 11 || i == 20 || i == 27) return 13;
    if (i == 5 || i == 12 || i == 21 || i == 28) return wideError;
    return 0;
}
static bool omitAsset(unsigned i) {
    return i == 6 || i == 7 || i == 13 || i == 14 || i == 15 || i == 23 || i == 29 || i == 30 || i == 31;
}
static NSString* expectedAudience(unsigned i) {
    if (i == 16) return @"受众-β";
    if (i == 17) return @"";
    if (i == 23) return @"alias-value";
    return nil;
}
static void checkAudience(AudienceGetter getter, NSString* asset, NSString* expected) {
    NSString* value;
    @autoreleasepool { value = [getter(asset) retain]; }
    assert((!expected && !value) || [value isEqualToString:expected]);
    [value release];
}
static void sequential(void) {
    for (unsigned i = 0; i < 32; ++i) {
        id asset = [NSString stringWithFormat:@"org.linuxcode.operation.%u", i];
        if (omitAsset(i)) asset = (i == 7 || i == 15 || i == 31) ? (id)@42 : nil;
        if (i < 8) {
            const signed char values[] = {0,1,-128,-1,1,0,1,0};
            assert(setEnabled(asset, (BOOL)values[i]) == statusFor(i));
        } else if (i < 16) {
            NSString* value = i == 9 ? nil : i == 10 ? @"" : @"受众-β";
            int64_t code = i == 13 ? globalAudience(value) :
                i == 12 || i == 14 ? internalSetAudience(value, asset) : setAudience(value, asset);
            assert(code == statusFor(i));
        } else if (i < 24) {
            checkAudience(i == 23 ? internalAudience : getAudience, asset, expectedAudience(i));
        } else {
            NSURL* url = i == 25 || i == 30 ? nil :
                i == 26 ? [NSURL URLWithString:@"file:///tmp/pallas-fixture"] :
                [NSURL URLWithString:[NSString stringWithUTF8String:encodedUrl]];
            int64_t code = i == 29 ? globalUrl(url) : i == 30 ? internalGlobalUrl(url) :
                i == 31 ? internalSetUrl(url, asset) : setUrl(url, asset);
            assert(code == statusFor(i));
        }
    }
}
static void* worker(void* context) {
    unsigned thread = (unsigned)(uintptr_t)context;
    @autoreleasepool {
        for (unsigned i = 0; i < 8; ++i) {
            NSString* asset = [NSString stringWithFormat:@"org.linuxcode.mixed.%u.%u", thread, i];
            bool enabled = true; bool expected = (thread+i)%2;
            switch (i%5) {
            case 0: assert(!getEnabled(asset, &enabled) && enabled == expected); break;
            case 1: assert(!setEnabled(asset, expected)); break;
            case 2: checkAudience(getAudience, asset, @"concurrent-value"); break;
            case 3: assert(!setAudience(@"concurrent-audience", asset)); break;
            case 4: assert(!setUrl([NSURL URLWithString:@"https://example.invalid/concurrent"], asset)); break;
            }
        }
    }
    return NULL;
}
static void client(void) {
    @autoreleasepool {
        sequential();
        pthread_t threads[8];
        for (unsigned i = 0; i < 8; ++i) assert(!pthread_create(&threads[i], NULL, worker, (void*)(uintptr_t)i));
        for (unsigned i = 0; i < 8; ++i) assert(!pthread_join(threads[i], NULL));
        bool enabled = false;
        assert(!getEnabled(@"org.linuxcode.retry-once", &enabled) && enabled);
        enabled = true;
        assert(getEnabled(@"org.linuxcode.retry-limit", &enabled) == 1 && !enabled);
    }
}
struct checkin { mach_msg_header_t header; mach_msg_body_t body; mach_msg_port_descriptor_t receive, send; };
int main(int argc, char** argv) {
    assert(argc == 2); setbuf(stdout, NULL);
    void* h = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL); assert(h);
    const char* names[] = {"MAGetPallasEnabled","MASetPallasEnabled","MAGetPallasAudience",
        "_MAsendGetPallasAudience","MASetPallasAudienceForType","_MAsendSetPallasAudience",
        "MASetPallasUrlForType","_MAsendSetPallasUrlForType","MASetPallasAudience",
        "MASetPallasUrl","_MAsendSetPallasUrl"};
    void* functions[11]; Dl_info first;
    for (unsigned i = 0; i < 11; ++i) {
        functions[i] = dlsym(h,names[i]); Dl_info info;
        assert(functions[i] && dladdr(functions[i], &info) && !strcmp(info.dli_fname,argv[1]));
        if (i == 0) first = info; else assert(first.dli_fbase == info.dli_fbase);
    }
    getEnabled=functions[0]; setEnabled=functions[1]; getAudience=functions[2]; internalAudience=functions[3];
    setAudience=functions[4]; internalSetAudience=functions[5]; setUrl=functions[6]; internalSetUrl=functions[7];
    globalAudience=functions[8]; globalUrl=functions[9]; internalGlobalUrl=functions[10];
    puts("PALLAS_ALL_DVT_OPERATIONS_AND_DEFAULT_ALIASES_OWNED_BY_SOURCE_FRAMEWORK_OK");
    mach_port_t existing;
    assert(bootstrap_look_up(bootstrap_port,(char*)service,&existing)==BOOTSTRAP_UNKNOWN_SERVICE);
    @autoreleasepool {
        assert(!getAudience(nil) && !internalAudience(@"absent"));
        assert(setEnabled(nil,YES)==1 && setAudience(nil,nil)==1 && globalAudience(@"value")==1);
        assert(setUrl(nil,nil)==1 && globalUrl(nil)==1 && internalGlobalUrl(nil)==1);
        assert(setAudience((id)@42,nil)==1);
        assert(setUrl((id)@"https://example.invalid",nil)==5 && setUrl((id)@42,nil)==5);
    }
    puts("PALLAS_ABSENT_SERVICE_STRING_NIL_STATUS_ERRORS_AND_INVALID_NSURL_PRECEDENCE_OK");
    mach_port_t receiver;
    assert(!mach_port_allocate(mach_task_self(),MACH_PORT_RIGHT_RECEIVE,&receiver));
    assert(!mach_port_insert_right(mach_task_self(),receiver,receiver,MACH_MSG_TYPE_MAKE_SEND));
    assert(!bootstrap_register(bootstrap_port,(char*)service,receiver));
    pid_t child=fork(); assert(child>=0);
    if (!child) { client(); _exit(0); }
    bool seen[8][8]={{false}};
    for (unsigned i=0; i<100; ++i) {
        @autoreleasepool {
            union { struct checkin checkin; unsigned char bytes[512]; } message={0};
            assert(!mach_msg(&message.checkin.header,MACH_RCV_MSG|MACH_RCV_TIMEOUT,0,sizeof(message),receiver,10000,MACH_PORT_NULL));
            assert(message.checkin.header.msgh_id==0x77303074 && message.checkin.body.msgh_descriptor_count==2);
            mach_port_t transport=message.checkin.receive.name;
            xpc_object_t request=NULL; assert(!xpc_pipe_receive(transport,&request,0) && request);
            assert(!strcmp(xpc_dictionary_get_string(request,"requestType"),"requestTypeSync"));
            assert(!strcmp(xpc_dictionary_get_string(request,"clientName"),getprogname()));
            uuid_t uuid; assert(!uuid_parse(xpc_dictionary_get_string(request,"connectionIdentifier"),uuid));
            const char* asset=xpc_dictionary_get_string(request,"AssetType");
            int action; bool enabled=false; int64_t code=0;
            const char* audience=NULL; const char* url=NULL; bool clear=false;
            if (i<32) {
                action=i<8?33:i<16?10:i<24?20:9; code=statusFor(i);
                if (omitAsset(i)) assert(!xpc_dictionary_get_value(request,"AssetType"));
                else { char name[64]; snprintf(name,sizeof(name),"org.linuxcode.operation.%u",i); assert(asset && !strcmp(asset,name)); }
                const bool values[]={false,true,true,true,true,false,true,false};
                if (action==33) enabled=values[i];
                if (action==10 && i!=9) audience=i==10?"":"受众-β";
                if (action==9) { clear=i==25||i==30; if (!clear) url=i==26?"file:///tmp/pallas-fixture":encodedUrl; }
            } else if (i<96) {
                unsigned thread,j; char tail;
                assert(asset && sscanf(asset,"org.linuxcode.mixed.%u.%u%c",&thread,&j,&tail)==2);
                assert(thread<8 && j<8 && !seen[thread][j]); seen[thread][j]=true;
                const int actions[]={32,33,20,10,9}; action=actions[j%5]; enabled=(thread+j)%2;
                if (action==10) audience="concurrent-audience";
                if (action==9) url="https://example.invalid/concurrent";
            } else {
                assert(asset && !strcmp(asset,i<98?"org.linuxcode.retry-once":"org.linuxcode.retry-limit"));
                action=32; enabled=true;
            }
            assert(xpc_get_type(xpc_dictionary_get_value(request,"messageAction"))==XPC_TYPE_INT64);
            assert(xpc_dictionary_get_int64(request,"messageAction")==action);
            if (action==33) {
                assert(xpc_get_type(xpc_dictionary_get_value(request,"pallasEnabled"))==XPC_TYPE_BOOL);
                assert(xpc_dictionary_get_bool(request,"pallasEnabled")==enabled);
            } else assert(!xpc_dictionary_get_value(request,"pallasEnabled"));
            const char* actualAudience=xpc_dictionary_get_string(request,"pallasAudience");
            assert(audience?(actualAudience && !strcmp(actualAudience,audience)):!xpc_dictionary_get_value(request,"pallasAudience"));
            const char* actualUrl=xpc_dictionary_get_string(request,"pallasUrl");
            assert(url?(actualUrl && !strcmp(actualUrl,url)):!xpc_dictionary_get_value(request,"pallasUrl"));
            assert(clear?xpc_dictionary_get_bool(request,"serverOverrideClear"):!xpc_dictionary_get_value(request,"serverOverrideClear"));
            bool drop=i==96||i>=98;
            if (!drop) {
                xpc_object_t reply=xpc_dictionary_create_reply(request); assert(reply);
                xpc_dictionary_set_int64(reply,"Result",code);
                if (action==32) xpc_dictionary_set_bool(reply,"pallasEnabled",enabled);
                if (action==20) {
                    if (i==19) xpc_dictionary_set_bool(reply,"pallasAudience",true);
                    else if (i!=18) {
                        const char* text=i>=32?"concurrent-value":i==16?"受众-β":i==17?"":i==22?"\xff":i==23?"alias-value":"must-not-be-returned";
                        xpc_dictionary_set_string(reply,"pallasAudience",text);
                    }
                }
                assert(!xpc_pipe_routine_reply(reply)); xpc_release(reply);
            }
            xpc_release(request);
            assert(!mach_port_destroy(mach_task_self(),transport));
            assert(!mach_port_deallocate(mach_task_self(),message.checkin.send.name));
        }
    }
    int status; assert(waitpid(child,&status,0)==child && WIFEXITED(status) && !WEXITSTATUS(status));
    assert(!mach_port_destroy(mach_task_self(),receiver));
    puts("PALLAS_REAL_XPC_32_SEQUENTIAL_SETTERS_STRING_GETTER_UTF8_POOL_LIFETIME_URL_CLEAR_DEFAULTS_AND_WIDE_ERRORS_OK");
    puts("PALLAS_REAL_XPC_EIGHT_THREADS_64_MIXED_FIVE_OPERATION_REQUEST_REPLY_CYCLES_OK");
    puts("PALLAS_REAL_XPC_PEER_TEARDOWN_ONE_RETRY_SUCCESS_AND_TWO_ATTEMPT_LIMIT_OK");
    return 0;
}
