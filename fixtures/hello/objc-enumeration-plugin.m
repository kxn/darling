#import <Foundation/Foundation.h>
#include <objc/runtime.h>
#include <assert.h>
#include <string.h>
@interface LinuxcodeEnumerationPluginBase : NSObject @end
@implementation LinuxcodeEnumerationPluginBase @end
@interface LinuxcodeEnumerationPluginChild : LinuxcodeEnumerationPluginBase @end
@implementation LinuxcodeEnumerationPluginChild @end
typedef void (*Enumerate)(const void *,const char *,Protocol *,Class,void (^)(Class,BOOL *));
unsigned linuxcode_enumerate_from_plugin(Enumerate enumerate) {
    __block unsigned count=0;
    enumerate(NULL,"LinuxcodeEnumeration",NULL,Nil,^(Class cls,BOOL *stop) {
        assert(!strncmp(class_getName(cls),"LinuxcodeEnumerationPlugin",26));count++;
    });
    return count;
}
