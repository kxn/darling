#import <Foundation/Foundation.h>
#import <dispatch/dispatch.h>
#import <dlfcn.h>
#import <objc/runtime.h>
#import "SecItemCloudRPC.h"
#import <ipc/securityd_client.h>
#include <stdio.h>
#include <string.h>
#include "native-current-item-layout.h"
extern void DarlingModernSecItemFetchCurrentItemAcrossAllDevices(CFStringRef,CFStringRef,CFStringRef,bool,void(^)(CFDataRef,CFErrorRef));

static _Atomic unsigned checks;
#define CHECK(...) do { ++checks; if (!(__VA_ARGS__)) { fprintf(stderr,"FAIL line=%d %s\n",__LINE__,#__VA_ARGS__); exit(1); } } while(0)

// Fixture backend only: validates transport and forwards deliberate test errors.
// It provides no keychain, authorization, or cloud storage implementation.
@interface CloudRPCFixture : NSObject <NSXPCListenerDelegate>
@property unsigned calls;
@property NSData *lastRef;
@property NSDate *lastDate;
@end
@implementation CloudRPCFixture
- (void)secItemFetchCurrentItemAcrossAllDevices:(NSString*)group identifier:(NSString*)identifier viewHint:(NSString*)view fetchCloudValue:(bool)fetch complete:(void(^)(NSData*,NSDate*,NSError*))reply {
    CHECK([group isEqual:@"fixture.中文"]);CHECK([view isEqual:@"zone"]);
    CHECK(fetch==![identifier isEqual:@"no-date"]);
    self.calls++;
    self.lastRef=([identifier isEqual:@"missing"] || [identifier isEqual:@"error"]) ? nil : [NSMutableData dataWithBytes:"a\0b\xff" length:4];
    self.lastDate=[identifier isEqual:@"no-date"] ? nil : [NSDate dateWithTimeIntervalSince1970:12345.25];
    NSError *error=([identifier isEqual:@"error"] || [identifier isEqual:@"partial"]) ? [NSError errorWithDomain:@"CloudRPCFixture" code:764 userInfo:nil] : nil;
    reply(self.lastRef,self.lastDate,error);
}
- (void)secItemUnsetCurrentItemsAcrossAllDevices:(NSString*)group identifiers:(NSArray*)identifiers viewHint:(NSString*)view complete:(void(^)(NSError*))reply {
    CHECK([group isEqual:@"fixture.中文"]);CHECK([identifiers isEqual:@[@"a",@"β"]]);CHECK([view isEqual:@"zone"]);
    self.calls++;reply([NSError errorWithDomain:@"CloudRPCFixture" code:761 userInfo:@{NSLocalizedDescriptionKey:@"deliberate unset failure"}]);
}
- (void)secItemFetchCurrentItemOutOfBand:(NSArray*)queries forceFetch:(bool)force complete:(void(^)(NSArray*,NSError*))reply {
    CHECK(queries.count==1);CHECK([queries[0] isKindOfClass:[CKKSCurrentItemQuery class]]);CHECK(force);
    CKKSCurrentItemQuery *q=queries[0];CHECK([q.identifier isEqual:@"item"]);CHECK([q.accessGroup isEqual:@"fixture.中文"]);CHECK([q.zoneID isEqual:@"zone"]);
    self.calls++;reply(@[[[CKKSCurrentItemQueryResult alloc] initWithIdentifier:q.identifier accessGroup:q.accessGroup zoneID:q.zoneID decryptedRecord:@{@"data":[NSData dataWithBytes:"a\0b" length:3]}]], [NSError errorWithDomain:@"CloudRPCFixture" code:762 userInfo:nil]);
}
- (void)secItemFetchPCSIdentityByKeyOutOfBand:(NSArray*)queries forceFetch:(bool)force complete:(void(^)(NSArray*,NSError*))reply {
    CHECK(queries.count==1);CHECK([queries[0] isKindOfClass:[CKKSPCSIdentityQuery class]]);CHECK(!force);
    CKKSPCSIdentityQuery *q=queries[0];CHECK([q.serviceNumber isEqual:@42]);CHECK([q.accessGroup isEqual:@"fixture.中文"]);CHECK([q.publicKey isEqual:@"YWJj"]);CHECK([q.zoneID isEqual:@"zone"]);
    self.calls++;reply(@[[[CKKSPCSIdentityQueryResult alloc] initWithServiceNumber:q.serviceNumber publicKey:q.publicKey zoneID:q.zoneID decryptedRecord:@{@"value":@7}]], [NSError errorWithDomain:@"CloudRPCFixture" code:763 userInfo:nil]);
}
- (BOOL)listener:(NSXPCListener*)listener shouldAcceptNewConnection:(NSXPCConnection*)connection {
    NSXPCInterface *iface=[NSXPCInterface interfaceWithProtocol:@protocol(SecuritydXPCProtocol)];
    [SecuritydXPCClient configureSecuritydXPCProtocol:iface];
    connection.exportedInterface=iface;connection.exportedObject=self;[connection resume];return YES;
}
@end

static NSArray *currentQueries(void) {return @[[[CKKSCurrentItemQuery alloc] initWithIdentifier:@"item" accessGroup:@"fixture.中文" zoneID:@"zone"]];}
static NSArray *pcsQueries(void) {return @[[[CKKSPCSIdentityQuery alloc] initWithServiceNumber:@42 accessGroup:@"fixture.中文" publicKey:@"YWJj" zoneID:@"zone"]];}
static void currentReply(NSArray *items,NSError *error) {
    CHECK([error.domain isEqual:@"CloudRPCFixture"] && error.code==762);CHECK(items.count==1);
    CKKSCurrentItemQueryResult *item=items[0];CHECK([item isKindOfClass:[CKKSCurrentItemQueryResult class]]);CHECK([item.identifier isEqual:@"item"]);CHECK([item.decryptedRecord[@"data"] isEqual:[NSData dataWithBytes:"a\0b" length:3]]);
}
static void pcsReply(NSArray *items,NSError *error) {
    CHECK([error.domain isEqual:@"CloudRPCFixture"] && error.code==763);CHECK(items.count==1);
    CKKSPCSIdentityQueryResult *item=items[0];CHECK([item isKindOfClass:[CKKSPCSIdentityQueryResult class]]);CHECK([item.serviceNumber isEqual:@42]);CHECK([item.decryptedRecord[@"value"] isEqual:@7]);
}
int main(int argc,char **argv) {@autoreleasepool {
    CHECK(argc==2);const char *mode=argv[1];
    NSXPCInterface *iface=[NSXPCInterface interfaceWithProtocol:@protocol(SecuritydXPCProtocol)];CHECK(iface!=nil);
    [SecuritydXPCClient configureSecuritydXPCProtocol:iface];
    CHECK([[iface classesForSelector:@selector(secItemFetchCurrentItemOutOfBand:forceFetch:complete:) argumentIndex:0 ofReply:NO] containsObject:[CKKSCurrentItemQuery class]]);
    CHECK([[iface classesForSelector:@selector(secItemFetchCurrentItemOutOfBand:forceFetch:complete:) argumentIndex:0 ofReply:YES] containsObject:[CKKSCurrentItemQueryResult class]]);
    CHECK([[iface classesForSelector:@selector(secItemFetchPCSIdentityByKeyOutOfBand:forceFetch:complete:) argumentIndex:0 ofReply:NO] containsObject:[CKKSPCSIdentityQuery class]]);
    CHECK([[iface classesForSelector:@selector(secItemFetchPCSIdentityByKeyOutOfBand:forceFetch:complete:) argumentIndex:0 ofReply:YES] containsObject:[CKKSPCSIdentityQueryResult class]]);
    CHECK([[iface classesForSelector:@selector(secItemUnsetCurrentItemsAcrossAllDevices:identifiers:viewHint:complete:) argumentIndex:0 ofReply:YES] containsObject:[NSError class]]);
    Dl_info info;CHECK(dladdr((void*)&SecItemUnsetCurrentItemsAcrossAllDevices,&info));CHECK(strstr(info.dli_fname,"libDarlingSecurityCloudRPC.dylib")!=NULL);
    void *security=dlopen("/System/Library/Frameworks/Security.framework/Security",RTLD_LAZY|RTLD_LOCAL);CHECK(security!=NULL);
    CHECK(dlsym(security,"gSecurityd")==&gSecurityd);
    CHECK(dlsym(security,"SecItemUnsetCurrentItemsAcrossAllDevices")==&SecItemUnsetCurrentItemsAcrossAllDevices);
    CHECK(dlsym(security,"SecItemFetchCurrentItemOutOfBand")==&SecItemFetchCurrentItemOutOfBand);
    CHECK(dlsym(security,"SecItemFetchPCSIdentityOutOfBand")==&SecItemFetchPCSIdentityOutOfBand);
    CHECK(dlsym(security,"SecItemFetchCurrentItemDataAcrossAllDevices")==&SecItemFetchCurrentItemDataAcrossAllDevices);
    CHECK(dlsym(security,"SecItemFetchCurrentItemAcrossAllDevices")!=&DarlingModernSecItemFetchCurrentItemAcrossAllDevices);
    CHECK(dlsym(security,"OBJC_CLASS_$_SecItemCurrentItemData")==(__bridge void*)[SecItemCurrentItemData class]);
    CHECK(class_getInstanceSize([SecItemCurrentItemData class])==native_current_item_size);
    CHECK(ivar_getOffset(class_getInstanceVariable([SecItemCurrentItemData class],"_persistentRef"))==native_current_item_ref_offset);
    CHECK(ivar_getOffset(class_getInstanceVariable([SecItemCurrentItemData class],"_currentItemPointerModificationTime"))==native_current_item_date_offset);
    CHECK([[iface classesForSelector:@selector(secItemFetchCurrentItemAcrossAllDevices:identifier:viewHint:fetchCloudValue:complete:) argumentIndex:2 ofReply:YES] containsObject:[NSError class]]);
    if (!strcmp(mode,"configuration")) { printf("SECURITY_CLOUD_RPC_CONFIGURATION_OK checks=%u\n",checks);return 0; }
    if (!strcmp(mode,"local")) {
        struct securityd *saved=gSecurityd;struct securityd fixture={0};CloudRPCFixture *backend=[CloudRPCFixture new];
        fixture.secd_xpc_server=(__bridge CFTypeRef)backend;gSecurityd=&fixture;
        __block unsigned replies=0;
        SecItemUnsetCurrentItemsAcrossAllDevices(CFSTR("fixture.中文"),(__bridge CFArrayRef)@[@"a",@"β"],CFSTR("zone"),^(CFErrorRef error){CHECK(error!=NULL);CHECK(CFErrorGetCode(error)==761);replies++;});
        SecItemFetchCurrentItemOutOfBand(currentQueries(),true,^(NSArray *items,NSError *error){currentReply(items,error);replies++;});
        SecItemFetchPCSIdentityOutOfBand(pcsQueries(),false,^(NSArray *items,NSError *error){pcsReply(items,error);replies++;});
        for (NSString *identifier in @[@"success",@"missing",@"error",@"partial",@"no-date"]) {
            BOOL expectData=![identifier isEqual:@"missing"] && ![identifier isEqual:@"error"];
            BOOL expectError=[identifier isEqual:@"error"] || [identifier isEqual:@"partial"];
            __block SecItemCurrentItemData *savedResult;
            @autoreleasepool {
                SecItemFetchCurrentItemDataAcrossAllDevices(@"fixture.中文",identifier,@"zone",![identifier isEqual:@"no-date"],^(SecItemCurrentItemData *result,NSError *error){
                    CHECK((result!=nil)==expectData);CHECK((error!=nil)==expectError);
                    if(error)CHECK(error.code==764 && [error.domain isEqual:@"CloudRPCFixture"]);
                    if(result){CHECK([result isKindOfClass:[SecItemCurrentItemData class]]);CHECK(result.persistentRef==backend.lastRef);CHECK(result.currentItemPointerModificationTime==backend.lastDate);CHECK([result.persistentRef isEqual:[NSData dataWithBytes:"a\0b\xff" length:4]]);savedResult=result;}
                    replies++;
                });
            }
            if(expectData){CHECK(savedResult.persistentRef.length==4);((unsigned char*)((NSMutableData*)backend.lastRef).mutableBytes)[0]='z';CHECK(((const unsigned char*)savedResult.persistentRef.bytes)[0]=='z');}
            DarlingModernSecItemFetchCurrentItemAcrossAllDevices(CFSTR("fixture.中文"),(__bridge CFStringRef)identifier,CFSTR("zone"),![identifier isEqual:@"no-date"],^(CFDataRef data,CFErrorRef error){
                CHECK((data!=NULL)==expectData);CHECK((error!=NULL)==expectError);if(error)CHECK(CFErrorGetCode(error)==764);if(data)CHECK(CFDataGetLength(data)==4);replies++;
            });
        }
        CHECK(replies==13);CHECK(backend.calls==13);gSecurityd=saved;CHECK(gSecurityd==saved);
        printf("SECURITY_CLOUD_RPC_LOCAL_ARGUMENTS_ERRORS_OK checks=%u\n",checks);return 0;
    }
    if (!strcmp(mode,"unavailable")) {
        CHECK(gSecurityd==NULL);dispatch_semaphore_t done=dispatch_semaphore_create(0);NSObject *guard=[NSObject new];__block unsigned replies=0;
        void(^received)(NSError*)=^(NSError *error){@synchronized(guard){CHECK(error!=nil);CHECK(error.code!=0);printf("ACTUAL_SECURITYD_ERROR domain=%s code=%ld\n",error.domain.UTF8String,(long)error.code);replies++;}dispatch_semaphore_signal(done);};
        SecItemUnsetCurrentItemsAcrossAllDevices(CFSTR("fixture.中文"),(__bridge CFArrayRef)@[@"a",@"β"],CFSTR("zone"),^(CFErrorRef error){received((__bridge NSError*)error);});
        SecItemFetchCurrentItemOutOfBand(currentQueries(),true,^(NSArray *items,NSError *error){CHECK(items==nil);received(error);});
        SecItemFetchPCSIdentityOutOfBand(pcsQueries(),false,^(NSArray *items,NSError *error){CHECK(items==nil);received(error);});
        SecItemFetchCurrentItemDataAcrossAllDevices(@"fixture.中文",@"success",@"zone",YES,^(SecItemCurrentItemData *result,NSError *error){CHECK(result==nil);received(error);});
        for(unsigned i=0;i<4;i++)CHECK(dispatch_semaphore_wait(done,dispatch_time(DISPATCH_TIME_NOW,10*NSEC_PER_SEC))==0);
        CHECK(replies==4);printf("SECURITY_CLOUD_RPC_REAL_SERVICE_ERROR_CALLBACKS_OK checks=%u\n",checks);return 0;
    }
    if (!strcmp(mode,"roundtrip")) {
        CloudRPCFixture *backend=[CloudRPCFixture new];NSXPCListener *listener=[NSXPCListener anonymousListener];listener.delegate=backend;[listener resume];
        NSXPCConnection *connection=[[NSXPCConnection alloc] initWithListenerEndpoint:listener.endpoint];connection.remoteObjectInterface=iface;[connection resume];
        dispatch_semaphore_t done=dispatch_semaphore_create(0);__block unsigned replies=0;
        id<SecuritydXPCProtocol> rpc=[connection remoteObjectProxyWithErrorHandler:^(NSError *error){fprintf(stderr,"TRANSPORT_ERROR %s\n",error.description.UTF8String);exit(2);}];
        [rpc secItemUnsetCurrentItemsAcrossAllDevices:@"fixture.中文" identifiers:@[@"a",@"β"] viewHint:@"zone" complete:^(NSError *error){CHECK(error.code==761);replies++;dispatch_semaphore_signal(done);}];
        [rpc secItemFetchCurrentItemOutOfBand:currentQueries() forceFetch:true complete:^(NSArray *items,NSError *error){currentReply(items,error);replies++;dispatch_semaphore_signal(done);}];
        [rpc secItemFetchPCSIdentityByKeyOutOfBand:pcsQueries() forceFetch:false complete:^(NSArray *items,NSError *error){pcsReply(items,error);replies++;dispatch_semaphore_signal(done);}];
        for(unsigned i=0;i<3;i++)CHECK(dispatch_semaphore_wait(done,dispatch_time(DISPATCH_TIME_NOW,10*NSEC_PER_SEC))==0);
        CHECK(replies==3);CHECK(backend.calls==3);[connection invalidate];[listener invalidate];
        printf("SECURITY_CLOUD_RPC_ANONYMOUS_NSXPC_FIXTURE_ROUNDTRIP_OK checks=%u\n",checks);return 0;
    }
    return 2;
}}
