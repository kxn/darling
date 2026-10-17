#import <Foundation/Foundation.h>
#import <objc/runtime.h>
#include <assert.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <uuid/uuid.h>

@interface RemoteDeviceQuery : NSObject
+ (id)wildcard;
- (int)type;
- (void)setType:(int)value;
- (const char *)name;
- (void)setName:(const char *)value;
- (const unsigned char *)uuid;
- (void)setUuid:(const unsigned char *)value;
- (const char *)availableService;
- (void)setAvailableService:(const char *)value;
@end
@interface NSData (PinnedSha256)
- (NSData *)sha256;
@end

int main(int argc, char **argv) {
    if (argc != 2 && argc != 3) return 2;
    setbuf(stdout, NULL);
    @autoreleasepool {
        void *image = dlopen(argv[1], RTLD_LAZY | RTLD_LOCAL);
        if (!image) { fprintf(stderr, "%s\n", dlerror()); return 1; }
        if (argc == 3) {
            // Negative probe of the actual restored lazy pointer. A missing
            // Security API must terminate binding, never manufacture a chain.
            Class cls = objc_getClass("RemoteDeviceQuery");
            Dl_info location;
            assert(dladdr((void *)class_getMethodImplementation(cls,@selector(init)), &location));
            size_t offset = strtoull(argv[2],NULL,0);
            CFArrayRef (*missing)(void *) = *(void **)((char *)location.dli_fbase+offset);
            puts("CALLING_ORIGINAL_MISSING_SECURITY_IMPORT");
            missing(NULL);
            abort();
        }
        const char *names[] = {"OS_remote_device", "OS_remote_device_browser",
            "OS_remote_listening_service", "OS_remote_pending_event", "OS_remote_service",
            "RemoteDeviceQuery", "SocketRemoteXpcProxy"};
        for (unsigned i = 0; i != 7; ++i) {
            Class cls = objc_getClass(names[i]);
            assert(cls && class_getSuperclass(cls) == [NSObject class]);
            unsigned count = 0;
            Method *methods = class_copyMethodList(cls, &count);
            assert(methods && count);
            for (unsigned j = 0; j < count; ++j) {
                assert(strlen(sel_getName(method_getName(methods[j]))) > 0);
                assert(strlen(method_getTypeEncoding(methods[j])) > 0);
                assert(method_getImplementation(methods[j]));
            }
            free(methods);
        }
        assert(objc_getProtocol("RemoteDeviceCommon"));
        puts("ORIGINAL_RSD_CLASSES_PROTOCOL_REGISTERED_OK");
        Class queryClass = objc_getClass("RemoteDeviceQuery");
        RemoteDeviceQuery *query = [[queryClass alloc] init];
        assert(query && [query type] == 0xffff);
        [query setType:3]; assert([query type] == 3);
        char name[] = "Linux x86 query";
        [query setName:name]; name[0] = 'X';
        assert(strcmp([query name], "Linux x86 query") == 0);
        [query setAvailableService:"com.example.service"];
        assert(strcmp([query availableService], "com.example.service") == 0);
        uuid_t uuid;
        assert(uuid_parse("00112233-4455-6677-8899-aabbccddeeff", uuid) == 0);
        [query setUuid:uuid]; uuid[0] = 0xff;
        assert([query uuid][0] == 0 && [query uuid][15] == 0xff);
        [query setName:NULL]; [query setUuid:NULL]; [query setAvailableService:NULL];
        assert(![query name] && ![query uuid] && ![query availableService]);
        [query release];
        RemoteDeviceQuery *wildcard = [queryClass wildcard];
        assert(wildcard && [wildcard type] == 0xffff);
        puts("ORIGINAL_RSD_QUERY_INIT_COPY_MUTATE_DEALLOC_OK");
        const unsigned char expected[] = {0xba,0x78,0x16,0xbf,0x8f,0x01,0xcf,0xea,
            0x41,0x41,0x40,0xde,0x5d,0xae,0x22,0x23,0xb0,0x03,0x61,0xa3,
            0x96,0x17,0x7a,0x9c,0xb4,0x10,0xff,0x61,0xf2,0x00,0x15,0xad};
        NSData *hash = [[NSData dataWithBytes:"abc" length:3] sha256];
        assert([hash isKindOfClass:[NSData class]] && hash.length == 32);
        assert(memcmp(hash.bytes, expected, 32) == 0);
        puts("ORIGINAL_RSD_NSDATA_CATEGORY_SHA256_VECTOR_OK");
    }
}
