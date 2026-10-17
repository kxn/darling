#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <objc/runtime.h>
static unsigned checks;
#define CHECK(c) do { checks++; if(!(c)){fprintf(stderr,"MDNS_NATIVE_FAIL %d %s\n",__LINE__,#c);abort();} } while(0)
int main(int argc,char **argv){
    setbuf(stdout,NULL);
    if(argc>1&&!strcmp(argv[1],"remote")){
        const char *paths[]={"/System/Library/PrivateFrameworks/RemoteXPC.framework/Versions/A/RemoteXPC","/System/Library/PrivateFrameworks/RemoteServiceDiscovery.framework/Versions/A/RemoteServiceDiscovery"};
        const char *classes[]={"OS_xpc_remote_channel","OS_xpc_remote_connection","OS_xpc_remote_listener","OS_xpc_remote_message","OS_xpc_remote_outstanding_reply","OS_xpc_remote_pending_stream","OS_xpc_remote_stream","OS_remote_device","OS_remote_device_browser","OS_remote_listening_service","OS_remote_pending_event","OS_remote_service","RemoteDeviceQuery","SocketRemoteXpcProxy"};
        for(unsigned i=0;i<2;i++){void *handle=dlopen(paths[i],RTLD_LAZY);if(!handle){fprintf(stderr,"REMOTE_NATIVE_DLOPEN_FAILED %s\n",dlerror());return 3;}}
        for(unsigned i=0;i<14;i++){Class cls=objc_getClass(classes[i]);CHECK(cls);CHECK(!strcmp(class_getName(cls),classes[i]));CHECK(class_getInstanceSize(cls)>=sizeof(void*));CHECK(strstr(class_getImageName(cls),"/runtime/mdns-native/frameworks/"));}
        printf("ORIGINAL_REMOTE_XPC_AND_RSD_REAL_CLASS_REGISTRATION_OK checks=%u classes=14\n",checks);return 0;
    }
    void *lib=dlopen("/usr/lib/libmdns.dylib",argc>1?RTLD_NOW:RTLD_LAZY);
    if(!lib){fprintf(stderr,"MDNS_NATIVE_DLOPEN_FAILED %s\n",dlerror());return 2;}
    size_t (*required)(uint16_t)=dlsym(lib,"mdns_tlv16_get_required_length");
    int (*set)(uint8_t*,const uint8_t*,uint16_t,uint16_t,const void*,uint8_t**)=dlsym(lib,"mdns_tlv16_set");
    int (*get)(const uint8_t*,const uint8_t*,uint16_t,size_t*,const uint8_t**,const uint8_t**)=dlsym(lib,"mdns_tlv16_get_value");
    CHECK(required&&set&&get);
    Dl_info owner;CHECK(dladdr((void*)get,&owner)&&strstr(owner.dli_fname,"/runtime/mdns-native/libraries/libmdns.dylib"));
    const unsigned lengths[]={0,1,2,7,16,31,255,256,4096,65535};
    for(unsigned c=0;c<sizeof(lengths)/sizeof(lengths[0]);c++){
        unsigned n=lengths[c];CHECK(required(n)==n+4);
        uint8_t *memory=malloc(n+20),*payload=malloc(n+1);CHECK(memory&&payload);
        for(unsigned i=0;i<n;i++)payload[i]=(uint8_t)(i*71+c);
        memset(memory,0xa5,n+20);uint8_t *start=memory+8,*next=NULL;
        uint16_t kind=(uint16_t)(0x8100+c);
        CHECK(set(start,start+n+4,kind,n,payload,&next)==0);CHECK(next==start+n+4);
        CHECK(start[0]==(kind>>8)&&start[1]==(kind&255));CHECK(start[2]==(n>>8)&&start[3]==(n&255));
        CHECK(!memcmp(start+4,payload,n));
        for(unsigned i=0;i<8;i++){CHECK(memory[i]==0xa5);CHECK(memory[n+12+i]==0xa5);}
        const uint8_t *value=NULL,*tail=NULL;size_t size=0;
        CHECK(get(start,next,kind,&size,&value,&tail)==0);CHECK(size==n&&value==start+4&&tail==next);
        size=123;value=(void*)1;tail=(void*)2;
        CHECK(get(start,next,kind+1,&size,&value,&tail)!=0);CHECK(size==123&&value==(void*)1&&tail==(void*)2);
        if(n){CHECK(get(start,next-1,kind,&size,&value,&tail)!=0);CHECK(size==123&&value==(void*)1&&tail==(void*)2);}
        free(payload);free(memory);
    }
    uint8_t sequence[]={0,1,0,2,0xde,0xad,0,2,0,1,0x7f};
    const uint8_t *value=NULL,*tail=NULL;size_t size=0;
    CHECK(get(sequence,sequence+sizeof(sequence),2,&size,&value,&tail)==0);CHECK(size==1&&value==sequence+10&&*value==0x7f&&tail==sequence+11);
    uint8_t tiny[8];memset(tiny,0xa5,sizeof(tiny));uint8_t *next=(void*)1;
    CHECK(set(tiny,tiny+3,1,0,NULL,&next)!=0);CHECK(next==(void*)1);
    for(unsigned i=0;i<8;i++)CHECK(tiny[i]==0xa5);
    CHECK(get(sequence+1,sequence,1,NULL,NULL,NULL)!=0);
    CHECK(get(sequence,sequence,1,NULL,NULL,NULL)!=0);
    CHECK(get(sequence,sequence+3,1,NULL,NULL,NULL)!=0);
    CHECK(get(sequence,sequence+6,1,NULL,NULL,NULL)==0);
    CHECK(dlclose(lib)==0);
    printf("ORIGINAL_MDNS_TLV16_BYTES_BOUNDS_AND_ERRORS_OK checks=%u mode=%s\n",checks,argc>1?"eager":"lazy");return 0;
}
