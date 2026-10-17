#import <Foundation/Foundation.h>
#import <CoreFoundation/CFURL.h>
#import <objc/runtime.h>
#include <assert.h>

// Existing Darling NSURL.m uses this accessor for its CFURL operations.
@interface NSURL (DarlingExistingCFURLAccessor)
- (CFURLRef)_cfurl;
@end

static BOOL directoryPath(id self,SEL command) {
    (void)command;
    return CFURLHasDirectoryPath([(NSURL *)self _cfurl]);
}

__attribute__((constructor)) static void addDirectoryPath(void) {
    Class cls=objc_getClass("NSURL");
    SEL selector=sel_registerName("hasDirectoryPath");
    assert(cls);
    if (class_getInstanceMethod(cls,selector))return;
    assert(class_getInstanceMethod(cls,sel_registerName("_cfurl")));
    assert(class_addMethod(cls,selector,(IMP)directoryPath,"c@:"));
}
