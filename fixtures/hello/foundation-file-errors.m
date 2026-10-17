#import <Foundation/Foundation.h>
#include <assert.h>
#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>

typedef NSError *(*Factory)(NSInteger,id,BOOL,id);
typedef NSError *(*ExtraFactory)(NSInteger,id,BOOL,id,NSDictionary *);
struct Mapping { NSInteger posix,read,write; };
static const struct Mapping mappings[]={
 {EPERM,257,513},{EACCES,257,513},{ENOENT,260,4},{EFBIG,263,512},
 {ENAMETOOLONG,258,514},{ENOSPC,256,640},{EDQUOT,256,640},{EROFS,256,642},
 {EEXIST,256,516},{EINVAL,256,512},{ENOMEM,256,512},{ENOTDIR,256,512}
};
int main(void) {
    @autoreleasepool {
        void *foundation=dlopen("/System/Library/Frameworks/Foundation.framework/Versions/C/Foundation",RTLD_LAZY|RTLD_LOCAL);assert(foundation);
        Factory create=dlsym(foundation,"_NSErrorWithFilePathErrnoAndVariant");assert(create);
        ExtraFactory extended=dlsym(foundation,"_NSErrorWithFilePathErrnoVariantAndExtraUserInfo");assert(extended);
        id paths[]={nil,@"/tmp/missing-中文",[NSURL fileURLWithPath:@"/tmp/missing-中文"]};
        unsigned trials=0;
        for(unsigned m=0;m<sizeof(mappings)/sizeof(mappings[0]);m++)for(unsigned reading=0;reading<2;reading++)
        for(unsigned p=0;p<3;p++)for(unsigned v=0;v<2;v++)for(unsigned e=0;e<2;e++) {
            id variant=v?@"operation":nil;
            NSDictionary *extra=e?@{NSUnderlyingErrorKey:@"spoof",NSFilePathErrorKey:@"override-path",
                @"NSUserStringVariant":@[@"override-variant"],@"custom":@"retained",NSLocalizedDescriptionKey:@"specific"}:nil;
            NSError *error=e?extended(mappings[m].posix,paths[p],reading,variant,extra):
                create(mappings[m].posix,paths[p],reading,variant);
            assert(error && [error.domain isEqualToString:NSCocoaErrorDomain]);
            assert(error.code==(reading?mappings[m].read:mappings[m].write));
            NSError *underlying=error.userInfo[NSUnderlyingErrorKey];
            assert([underlying isKindOfClass:[NSError class]] && [underlying.domain isEqualToString:NSPOSIXErrorDomain]);
            assert(underlying.code==mappings[m].posix);
            if(p==1)assert([error.userInfo[NSFilePathErrorKey] isEqual:paths[p]]);
            if(p==2)assert([error.userInfo[@"NSURL"] isEqual:paths[p]]);
            if(v)assert([error.userInfo[@"NSUserStringVariant"] isEqual:@[@"operation"]]);
            else if(e)assert([error.userInfo[@"NSUserStringVariant"] isEqual:@[@"override-variant"]]);
            else assert(!error.userInfo[@"NSUserStringVariant"]);
            if(e) {
                assert([error.userInfo[@"custom"] isEqual:@"retained"] && [error.localizedDescription isEqual:@"specific"]);
                if(p!=1)assert([error.userInfo[NSFilePathErrorKey] isEqual:@"override-path"]);
            }
            NSError *copy=[error copy];
            assert(copy && copy.code==error.code && [copy.domain isEqual:error.domain] && [copy.userInfo isEqual:error.userInfo]);
            [copy release];trials++;
        }
        printf("FOUNDATION_FILE_ERROR_NATIVE_ERRNO_MAPPINGS_PATH_URL_VARIANT_EXTRA_PRECEDENCE_COPY_OK %u\n",trials);
    }
    return 0;
}
