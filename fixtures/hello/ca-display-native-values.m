#import <Foundation/Foundation.h>
#include <CoreFoundation/CoreFoundation.h>
#include <objc/runtime.h>
#include <dlfcn.h>
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

@interface CADisplayMode : NSObject
+ (instancetype)displayModeWithWidth:(NSUInteger)width height:(NSUInteger)height refreshRate:(double)rate;
+ (instancetype)displayModeWithWidth:(NSUInteger)width height:(NSUInteger)height refreshRate:(double)rate isVRR:(signed char)vrr;
- (NSUInteger)width;
- (NSUInteger)height;
- (double)refreshRate;
- (signed char)isVRR;
- (signed char)isVirtual;
- (uint64_t)internalRepresentation;
- (CFDataRef)copyPrivateRepresentation;
@end

int main(int argc, char** argv) {
    setbuf(stdout,NULL); assert(argc==2);
    @autoreleasepool {
        puts("CA_DISPLAY_NATIVE_VALUES_MAIN_ENTERED");
        void* handle=dlopen(argv[1],RTLD_LAZY|RTLD_LOCAL);
        if (!handle) { fprintf(stderr,"CA_DISPLAY_NATIVE_DLOPEN_FAILED: %s\n",dlerror()); return 2; }
        Class cls=objc_getClass("CADisplayMode"); assert(cls);
        assert(dlsym(handle,"OBJC_CLASS_$_CADisplayMode")==cls);
        Method factory=class_getClassMethod(cls,@selector(displayModeWithWidth:height:refreshRate:));
        assert(factory); Dl_info owner;
        assert(dladdr((void*)method_getImplementation(factory),&owner));
        assert(strstr(owner.dli_fname,"runtime/quartzcore-native/frameworks/QuartzCore.framework/"));
        puts("CA_DISPLAY_NATIVE_CLASS_AND_FACTORY_OWNED_BY_ORIGINAL_QUARTZCORE_OK");
        const NSUInteger widths[]={0,1,640,1920,16383,16384,65535};
        const NSUInteger heights[]={0,1,1080,16383,16384};
        const double rates[]={0,23.976,59.94,60,120,144,240.1234};
        unsigned tested=0;
        for (unsigned w=0;w<7;++w) for (unsigned h=0;h<5;++h)
            for (unsigned r=0;r<7;++r) for (unsigned vrr=0;vrr<2;++vrr) {
                @autoreleasepool {
                    CADisplayMode* mode=vrr ? [cls displayModeWithWidth:widths[w] height:heights[h] refreshRate:rates[r] isVRR:1]
                        : [cls displayModeWithWidth:widths[w] height:heights[h] refreshRate:rates[r]];
                    assert(mode && [mode width]==(widths[w]&16383) && [mode height]==(heights[h]&16383));
                    uint64_t packed=(widths[w]&16383)|((heights[h]&16383)<<14)
                        |(((uint64_t)(int64_t)(rates[r]*65536)&0x1ffffff)<<29)
                        |0x1080000000000000ULL|((uint64_t)vrr<<63);
                    assert([mode internalRepresentation]==packed);
                    assert([mode hash]==packed && !![mode isVRR]==vrr && ![mode isVirtual]);
                    assert(fabs([mode refreshRate]-rates[r])<=0.011);
                    CADisplayMode* equal=[cls displayModeWithWidth:widths[w] height:heights[h] refreshRate:rates[r] isVRR:vrr];
                    assert([mode isEqual:equal] && [equal isEqual:mode]);
                    CFDataRef data=[mode copyPrivateRepresentation];
                    assert(data && CFGetTypeID(data)==CFDataGetTypeID() && CFDataGetLength(data)==16);
                    uint64_t words[2]; memcpy(words,CFDataGetBytePtr(data),sizeof(words));
                    assert(!words[0] && words[1]==packed);
                    CFMutableDataRef copy=CFDataCreateMutableCopy(NULL,0,data); assert(copy);
                    CFDataGetMutableBytePtr(copy)[8]^=0x80;
                    assert(!CFEqual(copy,data) && [mode internalRepresentation]==packed);
                    CFRelease(copy); CFRelease(data); ++tested;
                }
            }
        assert(tested==490);
        printf("CA_DISPLAY_ORIGINAL_NATIVE_FACTORY_DIMENSIONS_RATES_VRR_PACKING_EQUALITY_AND_DATA_COPY_OK %u\n",tested);
    }
    return 0;
}
