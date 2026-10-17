#import <Foundation/Foundation.h>
#import <objc/runtime.h>
#import <objc/message.h>
#include <assert.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

int main(int argc,char **argv) {
    if (argc<2 || argc>3)return 2;
    @autoreleasepool {
        void *image=dlopen(argv[1],RTLD_LAZY|RTLD_LOCAL);
        if (!image) { fprintf(stderr,"%s\n",dlerror());return 1; }
        Class cls=objc_getClass("MTLTextureInternal");assert(cls);
        assert(dlsym(image,"OBJC_CLASS_$_MTLTextureInternal")==cls);
        assert(class_getSuperclass(cls)==[NSObject class]);
        id object=[[cls alloc] init];assert(object && object_getClass(object)==cls);
        assert(class_getInstanceSize(cls)==class_getInstanceSize([NSObject class]));
        Method method=class_getInstanceMethod(cls,@selector(forwardInvocation:));Dl_info owner;
        assert(method && dladdr((void *)method_getImplementation(method),&owner));
        assert(strstr(owner.dli_fname,"/native-library-stage/libDarlingMetalLegacyHeadless.dylib"));
        if (argc==3) {
            assert(!strcmp(argv[2],"--unsupported"));
            ((NSUInteger(*)(id,SEL))objc_msgSend)(object,sel_registerName("width"));
            return 99;
        }
        [object release];
    }
    puts("DARLING_LEGACY_TEXTURE_CLASS_NATIVE_METAL_REEXPORT_IDENTITY_OWNER_OK");
    return 0;
}
