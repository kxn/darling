#import <Foundation/Foundation.h>
#include <CoreFoundation/CoreFoundation.h>
#include <assert.h>
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef CFStringRef (*Current)(uint32_t);
typedef CFStringRef (*CopyDescription)(uint32_t,uint32_t,CFStringRef);
typedef CFStringRef (*CopyCurrent)(void);
typedef CFBundleRef (*GetBundle)(void);
typedef uint32_t (*Scalar)(void);
typedef CFStringRef (*CopyKind)(Boolean);
static void checkedString(CFStringRef value) {
    assert(value && CFGetTypeID(value)==CFStringGetTypeID() && CFStringGetLength(value)>0);
}
int main(int argc,char** argv) {
    assert(argc==3);setbuf(stdout,NULL);
    CFURLRef url=CFURLCreateFromFileSystemRepresentation(NULL,(const UInt8*)argv[2],strlen(argv[2]),true);
    assert(url);CFBundleRef bundle=CFBundleCreate(NULL,url);CFRelease(url);assert(bundle);
    assert(CFEqual(CFBundleGetIdentifier(bundle),CFSTR("com.apple.AppleSystemInfo")));
    CFURLRef resource=CFBundleCopyResourceURL(bundle,CFSTR("AppleSystemInfo"),CFSTR("strings"),NULL);
    assert(resource);CFRelease(resource);
    void* h=dlopen(argv[1],RTLD_LAZY|RTLD_LOCAL);
    if(!h)fprintf(stderr,"%s\n",dlerror());assert(h);
    const char* names[]={"ASI_GetCurrentCPUDescriptionWithFormat","ASI_CopyCPUDescription",
        "ASI_CopyCurrentCPUDescription","ASI_GetFrameworkBundle","ASI_NumberOfCPUs","ASI_CPUSpeedInHz","ASI_CopyCPUKind"};
    void* functions[7];Dl_info owner;
    for(unsigned i=0;i<7;++i) {
        functions[i]=dlsym(h,names[i]);Dl_info info;
        assert(functions[i] && dladdr(functions[i],&info) && !strcmp(info.dli_fname,argv[1]));
        if(!i)owner=info;else assert(owner.dli_fbase==info.dli_fbase);
    }
    Current current=functions[0];CopyDescription copy=functions[1];CopyCurrent copyCurrent=functions[2];GetBundle getBundle=functions[3];
    Scalar cpus=functions[4],speed=functions[5];CopyKind kind=functions[6];
    assert(getBundle()==bundle);
    CFStringRef localized=CFBundleCopyLocalizedString(bundle,CFSTR("2xCPUFormat"),CFSTR("MISSING"),CFSTR("AppleSystemInfo"));
    char localizedText[128];assert(CFStringGetCString(localized,localizedText,sizeof(localizedText),kCFStringEncodingUTF8));
    printf("NATIVE_LOCALIZED_DUAL_FORMAT %s\n",localizedText);CFRelease(localized);
    puts("ORIGINAL_ASI_FUNCTION_OWNER_AND_ACTUAL_RESOURCE_BUNDLE_OK");
    const uint32_t counts[]={1,2,3,4,8};
    const uint32_t speeds[]={0,100000000,500000000,2500000000U,UINT32_MAX};
    for(unsigned i=0;i<5;++i)for(unsigned j=0;j<5;++j) {
        CFStringRef text=copy(counts[i],speeds[j],CFSTR("Fixture CPU"));checkedString(text);
        char output[256];assert(CFStringGetCString(text,output,sizeof(output),kCFStringEncodingUTF8));
        printf("NATIVE_SCALAR_CPU_DESCRIPTION %u %u %s\n",counts[i],speeds[j],output);
        assert(CFStringFind(text,CFSTR("Fixture CPU"),0).location!=kCFNotFound);
        /* Intel-prefixed resource keys in this image use the embedded
         * "2 x %@" fallback, rather than the older PowerPC "Dual %@" key. */
        if(counts[i]==2)assert(CFStringFind(text,CFSTR("2 x"),0).location!=kCFNotFound);
        if(speeds[j]==100000000)assert(CFStringFind(text,CFSTR("100 MHz"),0).location!=kCFNotFound);
        if(speeds[j]==500000000)assert(CFStringFind(text,CFSTR("500 MHz"),0).location!=kCFNotFound);
        CFStringRef retained=CFRetain(text);CFRelease(text);checkedString(retained);CFRelease(retained);
    }
    puts("ORIGINAL_ASI_CPU_DESCRIPTION_25_REAL_COUNT_SPEED_STRING_FORMAT_CASES_OK");
    for(unsigned shortNames=0;shortNames<2;++shortNames)for(uint32_t format=0;format<=4;++format) {
        CFStringRef retained;
        @autoreleasepool {retained=current(format|(shortNames?0x10000:0));checkedString(retained);CFRetain(retained);}
        checkedString(retained);
        char buffer[256];assert(CFStringGetCString(retained,buffer,sizeof(buffer),kCFStringEncodingUTF8));
        printf("NATIVE_CURRENT_CPU_DESCRIPTION %u %u %s\n",shortNames,format,buffer);
        CFRelease(retained);
    }
    @autoreleasepool {
        CFStringRef owned=copyCurrent();checkedString(owned);
        CFStringRef cpuKind=kind(false);
        CFStringRef localizedKind=cpuKind?CFBundleCopyLocalizedString(bundle,cpuKind,cpuKind,CFSTR("AppleSystemInfo")):NULL;
        CFStringRef expected=copy(cpus(),speed(),localizedKind?localizedKind:CFSTR("Unknown"));
        char output[256];assert(CFStringGetCString(owned,output,sizeof(output),kCFStringEncodingUTF8));
        printf("NATIVE_COPY_CURRENT_CPU_DESCRIPTION %s\n",output);
        checkedString(expected);char comparison[256];assert(CFStringGetCString(expected,comparison,sizeof(comparison),kCFStringEncodingUTF8));
        printf("NATIVE_COMPOSED_CPU_DESCRIPTION %u %u %s\n",cpus(),speed(),comparison);
        assert(CFEqual(owned,expected));
        CFRelease(expected);if(localizedKind)CFRelease(localizedKind);if(cpuKind)CFRelease(cpuKind);CFRelease(owned);
    }
    puts("ORIGINAL_ASI_CURRENT_TEN_FORMAT_FLAGS_COPY_WRAPPER_AND_AUTORELEASE_LIFETIME_OK");
    CFRelease(bundle);return 0;
}
