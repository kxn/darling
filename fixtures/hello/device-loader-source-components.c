#include <IOKit/IOKitLib.h>
#include <CoreFoundation/CoreFoundation.h>
#include <mach/mach.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#define CHECK(c) do { if(!(c)){fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#c);exit(1);} } while(0)
typedef kern_return_t (*port_fn)(mach_port_t,mach_port_t*);
static void same_backend(port_fn modern,port_fn legacy,mach_port_t bootstrap) {
    mach_port_t a=0,b=0;kern_return_t x=modern(bootstrap,&a),y=legacy(bootstrap,&b);
    printf("IOKIT_ACTUAL_BACKEND bootstrap=%u modern=%d legacy=%d modern_port=%u legacy_port=%u\n",bootstrap,x,y,a,b);
    CHECK(x==y);
    if(x==KERN_SUCCESS){mach_port_type_t type=0;CHECK(a&&b);CHECK(mach_port_type(mach_task_self(),a,&type)==KERN_SUCCESS&&(type&MACH_PORT_TYPE_SEND));CHECK(a==b);CHECK(mach_port_deallocate(mach_task_self(),a)==KERN_SUCCESS);CHECK(mach_port_deallocate(mach_task_self(),b)==KERN_SUCCESS);}
}
int main(void) {
    setbuf(stdout,NULL);
    port_fn modern=dlsym(RTLD_DEFAULT,"IOMainPort"),legacy=dlsym(RTLD_DEFAULT,"IOMasterPort");CHECK(modern&&legacy);
    Dl_info info={0};CHECK(dladdr((void*)modern,&info)&&strstr(info.dli_fname,"iokit-main-port-source/frameworks/IOKit.framework/"));
    CHECK(dladdr((void*)legacy,&info)&&strstr(info.dli_fname,"libDarlingIOKitBackend.dylib"));
    CHECK(kIOMainPortDefault==MACH_PORT_NULL&&kIOMasterPortDefault==MACH_PORT_NULL);
    same_backend(modern,legacy,MACH_PORT_NULL);same_backend(modern,legacy,0xdeadbeef);
    CFMutableDictionaryRef query=IOServiceMatching("LinuxcodeActualSourceMainPortProbe");CHECK(query&&CFGetTypeID(query)==CFDictionaryGetTypeID());CHECK(CFEqual(CFDictionaryGetValue(query,CFSTR("IOProviderClass")),CFSTR("LinuxcodeActualSourceMainPortProbe")));CFRelease(query);
    void *security=dlopen("/System/Library/Frameworks/Security.framework/Versions/A/Security",RTLD_LAZY|RTLD_LOCAL);CHECK(security);
    CFStringRef *identifier=dlsym(security,"kSecAttrKeyTypeSecureEnclaveAnonymousAttestation");CHECK(identifier&&*identifier&&CFGetTypeID(*identifier)==CFStringGetTypeID());CHECK(CFEqual(*identifier,CFSTR("2147483680")));
    void *crypto=dlopen("/System/Library/Frameworks/CryptoTokenKit.framework/Versions/A/CryptoTokenKit",RTLD_LAZY|RTLD_LOCAL);CHECK(crypto);
    CFStringRef *domain=dlsym(crypto,"TKErrorDomain");CHECK(domain&&*domain&&CFGetTypeID(*domain)==CFStringGetTypeID());CHECK(CFEqual(*domain,CFSTR("CryptoTokenKit")));
    puts("DEVICE_LOADER_ACTUAL_IOKIT_BACKEND_PORT_ERRORS_MATCHING_AND_NATIVE_SECURITY_TOKEN_CONSTANTS_OK");return 0;
}
