#import <Foundation/Foundation.h>
#include <objc/runtime.h>
#include <dlfcn.h>
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
@protocol LinuxcodeEnumerationMarker @end
@interface LinuxcodeEnumerationBase : NSObject <LinuxcodeEnumerationMarker> @end
@implementation LinuxcodeEnumerationBase @end
@interface LinuxcodeEnumerationChild : LinuxcodeEnumerationBase @end
@implementation LinuxcodeEnumerationChild @end
@interface LinuxcodeEnumerationGrandchild : LinuxcodeEnumerationChild @end
@implementation LinuxcodeEnumerationGrandchild @end
@interface LinuxcodeEnumerationUnrelated : NSObject @end
@implementation LinuxcodeEnumerationUnrelated @end
typedef void (*Enumerate)(const void *,const char *,Protocol *,Class,void (^)(Class,BOOL *));
extern Class *objc_copyRealizedClassList(unsigned int *);
static unsigned realized(void) { unsigned count=0;Class *classes=objc_copyRealizedClassList(&count);free(classes);return count; }
static unsigned enumerate_count(Enumerate enumerate,const void *image,const char *prefix,Protocol *protocol,Class superclass) {
    __block unsigned count=0;
    enumerate(image,prefix,protocol,superclass,^(Class cls,BOOL *stop) { assert(cls && stop);count++; });
    return count;
}
int main(int argc,char **argv) {
    assert(argc==3);
    void *helper=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);
    if (!helper) { fprintf(stderr,"%s\n",dlerror());return 1; }
    Enumerate enumerate=(Enumerate)dlsym(helper,"objc_enumerateClasses");assert(enumerate);
    void *plugin=dlopen(argv[2],RTLD_LAZY|RTLD_LOCAL);assert(plugin);
    unsigned (*fromPlugin)(Enumerate)=dlsym(plugin,"linuxcode_enumerate_from_plugin");assert(fromPlugin);
    unsigned before=realized();
    assert(enumerate_count(enumerate,NULL,"LinuxcodeEnumeration",NULL,Nil)==4);
    assert(realized()==before); // No realization for name-only enumeration.
    Dl_info appInfo,pluginInfo;assert(dladdr((void *)&main,&appInfo) && dladdr((void *)fromPlugin,&pluginInfo));
    assert(enumerate_count(enumerate,appInfo.dli_fbase,"LinuxcodeEnumeration",NULL,Nil)==4);
    assert(fromPlugin(enumerate)==2);
    assert(enumerate_count(enumerate,pluginInfo.dli_fbase,"LinuxcodeEnumeration",NULL,Nil)==2);
    assert(enumerate_count(enumerate,plugin,"LinuxcodeEnumeration",NULL,Nil)==2);
    void *first=dlopen(argv[2],RTLD_LAZY|RTLD_LOCAL|RTLD_FIRST);assert(first);
    assert(enumerate_count(enumerate,first,"LinuxcodeEnumeration",NULL,Nil)==2);dlclose(first);
    Class base=objc_getClass("LinuxcodeEnumerationBase");assert(base);
    Protocol *marker=objc_getProtocol("LinuxcodeEnumerationMarker");assert(marker);
    assert(enumerate_count(enumerate,appInfo.dli_fbase,"LinuxcodeEnumeration",marker,Nil)==3);
    assert(enumerate_count(enumerate,appInfo.dli_fbase,"LinuxcodeEnumeration",NULL,base)==2);
    assert(enumerate_count(enumerate,appInfo.dli_fbase,"LinuxcodeEnumeration",marker,base)==2);
    __block unsigned stopped=0;
    enumerate(appInfo.dli_fbase,"LinuxcodeEnumeration",NULL,Nil,^(Class cls,BOOL *stop) { stopped++;*stop=YES; });
    assert(stopped==1);
    Class dynamic=objc_allocateClassPair(objc_getClass("NSObject"),"LinuxcodeEnumerationDynamic",0);assert(dynamic);
    assert(class_addProtocol(dynamic,marker));objc_registerClassPair(dynamic);
    Class child=objc_allocateClassPair(dynamic,"LinuxcodeEnumerationDynamicChild",0);assert(child);objc_registerClassPair(child);
    Class pending=objc_allocateClassPair(dynamic,"LinuxcodeEnumerationDynamicPending",0);assert(pending);
    assert(enumerate_count(enumerate,OBJC_DYNAMIC_CLASSES,"LinuxcodeEnumerationDynamic",NULL,Nil)==2);
    assert(enumerate_count(enumerate,OBJC_DYNAMIC_CLASSES,"LinuxcodeEnumerationDynamic",marker,Nil)==2);
    assert(enumerate_count(enumerate,OBJC_DYNAMIC_CLASSES,"LinuxcodeEnumerationDynamic",NULL,dynamic)==1);
    objc_disposeClassPair(pending);objc_disposeClassPair(child);objc_disposeClassPair(dynamic);
    errno=0;assert(enumerate_count(enumerate,(void *)0x12345,NULL,NULL,Nil)==0 && errno==EINVAL);
    dlclose(plugin);
    puts("OBJC_ENUMERATION_CALLER_HEADER_HANDLES_FILTERS_DYNAMIC_STOP_AND_LAZY_METADATA_OK");
    return 0;
}
