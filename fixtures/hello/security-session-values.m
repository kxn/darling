#include "classes.h"
#include <objc/runtime.h>
#include <dlfcn.h>
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "native-layouts.h"
int main(int argc,char **argv) {
    assert(argc==2);
    NSAutoreleasePool *pool=[NSAutoreleasePool new];
    void *library=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);
    if (!library) { fprintf(stderr,"%s\n",dlerror());return 1; }
    for (unsigned i=0;i<sizeof(layouts)/sizeof(*layouts);i++) {
        Class cls=objc_getClass(layouts[i].name);assert(cls);
        assert(class_getInstanceSize(cls)==layouts[i].size);
        if (layouts[i].ivar) {
            Ivar field=class_getInstanceVariable(cls,layouts[i].ivar);assert(field);
            assert(ivar_getOffset(field)==layouts[i].offset);
        }
    }
    Class sessionClass=objc_getClass("SecSessionInfo");
    Method method=class_getInstanceMethod(sessionClass,sel_registerName("initWithPSK:::::"));
    Dl_info owner;assert(method && dladdr((void *)method_getImplementation(method),&owner));
    char *actual=realpath(owner.dli_fname,NULL),*expected=realpath(argv[1],NULL);
    assert(actual && expected && !strcmp(actual,expected));free(actual);free(expected);
    const uint32_t ages[]={0,1,0x80000000u,UINT32_MAX};
    const uint64_t times[]={0,1,1ull<<40,1ull<<63,UINT64_MAX};
    const unsigned char original[]={0,1,255,2,128,0,3,9};
    NSData *known=[NSData dataWithBytes:original length:sizeof(original)];
    for (unsigned a=0;a<4;a++) for (unsigned t=0;t<5;t++) {
        NSMutableData *psk=[known mutableCopy],*identity=[known mutableCopy];
        SecSessionInfo *session=[[sessionClass alloc] initWithPSK:psk :identity :ages[a] :times[t] :~times[t]];
        assert(session && [session.psk isEqual:known] && [session.psk_id isEqual:known]);
        assert(session.psk!=psk && session.psk_id!=identity);
        memset(psk.mutableBytes,7,psk.length);memset(identity.mutableBytes,8,identity.length);
        assert([session.psk isEqual:known] && [session.psk_id isEqual:known]);
        assert(session.ticket_age_add==ages[a] && session.ticket_creation_time==times[t] && session.ticket_lifetime==~times[t]);
        session.psk=psk;session.psk_id=identity;
        assert(session.psk==psk && session.psk_id==identity);
        session.ticket_age_add=~ages[a];session.ticket_creation_time=~times[t];session.ticket_lifetime=times[t];
        assert(session.ticket_age_add==~ages[a] && session.ticket_creation_time==~times[t] && session.ticket_lifetime==times[t]);
        [psk release];[identity release];assert(session.psk.length==sizeof(original));[session release];
    }
    for (unsigned alias=0;alias<2;alias++) {
        Class cls=objc_getClass(alias?"ExternalPreSharedKey":"SecExternalPreSharedKey");
        NSMutableData *identity=[known mutableCopy],*key=[known mutableCopy],*context=[known mutableCopy];
        SecExternalPreSharedKey *value=[[cls alloc] initWithExternalIdentity:identity :key :context];
        assert(value.external_identity==identity && value.epsk==key && value.context==context);
        memset(key.mutableBytes,11,key.length);assert(((const unsigned char *)value.epsk.bytes)[0]==11);
        [identity release];[key release];[context release];assert(value.context.length==sizeof(original));[value release];
        cls=objc_getClass(alias?"OfferedEPSK":"SecOfferedEPSK");
        SecOfferedEPSK *offered=[[cls alloc] initWithExternalIdentity:known :nil];
        assert(offered.external_identity==known && !offered.context);
        offered.context=known;assert(offered.context==known);[offered release];
    }
    [pool drain];
    puts("APPLE_SECURITY_SESSION_VALUES_NATIVE_LAYOUT_COPY_RETAIN_PROPERTIES_AND_ALIASES_OK");
    return 0;
}
