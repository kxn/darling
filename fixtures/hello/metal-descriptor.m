#import <Foundation/Foundation.h>
#import <Metal/MTLResidencySet.h>
#import <objc/runtime.h>
#include <assert.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

int main(int argc,char **argv) {
    if (argc!=2)return 2;
    @autoreleasepool {
        void *image=dlopen(argv[1],RTLD_LAZY|RTLD_LOCAL);
        if (!image) { fprintf(stderr,"%s\n",dlerror());return 1; }
        Class cls=objc_getClass("MTLResidencySetDescriptor");assert(cls);
        Method setter=class_getInstanceMethod(cls,@selector(setInitialCapacity:));Dl_info owner;
        assert(setter && dladdr((void *)method_getImplementation(setter),&owner));
        assert(strstr(owner.dli_fname,"Metal.framework")!=NULL);
        MTLResidencySetDescriptor *first=[cls new],*second=[cls new];
        assert(first && second && first!=second && first.initialCapacity==0 && first.label==nil);
        first.initialCapacity=7;
        NSMutableString *label=[NSMutableString stringWithString:@"original"];
        first.label=label;[label appendString:@"-changed"];
        assert([first.label isEqualToString:@"original"]);
        MTLResidencySetDescriptor *copy=[first copy];
        assert(copy && copy!=first && copy.initialCapacity==7 && [copy.label isEqualToString:@"original"]);
        copy.initialCapacity=11;copy.label=@"copied";
        assert(first.initialCapacity==7 && [first.label isEqualToString:@"original"]);
        assert(second.initialCapacity==0 && second.label==nil);
    }
    puts("ORIGINAL_METAL_RESIDENCY_DESCRIPTOR_DEFAULTS_LABEL_COPY_INDEPENDENT_STATE_OK");
    return 0;
}
