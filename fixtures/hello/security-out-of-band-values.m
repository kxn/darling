#import <Foundation/Foundation.h>
#import <CoreFoundation/CoreFoundation.h>
#import "SecItemFetchOutOfBandValues.h"
#include <objc/runtime.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include "native-layouts.h"
static unsigned checks;
static unsigned unexpectedDecodes;
@interface OOBUnexpectedValue:NSObject<NSSecureCoding>
@end
@implementation OOBUnexpectedValue
+(BOOL)supportsSecureCoding{return YES;}
-(void)encodeWithCoder:(NSCoder*)coder{}
-(instancetype)initWithCoder:(NSCoder*)coder{unexpectedDecodes++;return [super init];}
@end
#define CHECK(c) do{checks++;if(!(c)){fprintf(stderr,"SEC_OOB_VALUES_FAIL %d %s\n",__LINE__,#c);abort();}}while(0)
static id roundtrip(id value){NSError *error=nil;NSData *data=[NSKeyedArchiver archivedDataWithRootObject:value requiringSecureCoding:YES error:&error];CHECK(data&&error==nil);id decoded=[NSKeyedUnarchiver unarchivedObjectOfClass:[value class] fromData:data error:&error];CHECK(decoded&&error==nil&&decoded!=value);return decoded;}
int main(void){setbuf(stdout,NULL);@autoreleasepool{
    void *security=dlopen("/System/Library/Frameworks/Security.framework/Versions/A/Security",RTLD_LAZY);CHECK(security);
    CFStringRef *identifier=dlsym(security,"kSecUseSystemKeychainAlways");CHECK(identifier&&CFGetTypeID(*identifier)==CFStringGetTypeID()&&CFEqual(*identifier,CFSTR("u_SystemKeychainAlways")));
    for(unsigned i=0;i<sizeof(layouts)/sizeof(layouts[0]);i++){
        Class cls=objc_getClass(layouts[i].name);CHECK(cls&&class_getInstanceSize(cls)==layouts[i].size);
        Ivar field=class_getInstanceVariable(cls,layouts[i].ivar);CHECK(field&&ivar_getOffset(field)==layouts[i].offset);
        CHECK([cls supportsSecureCoding]);Dl_info owner;CHECK(dladdr((__bridge void*)cls,&owner)&&strstr(owner.dli_fname,"libDarlingSecurityOutOfBandValues.dylib"));
        char symbol[256];snprintf(symbol,sizeof(symbol),"OBJC_CLASS_$_%s",layouts[i].name);CHECK(dlsym(security,symbol)==(__bridge void*)cls);
    }
    NSDictionary *record=@{@"text":@"明文",@"number":@42,@"bytes":[NSData dataWithBytes:"a\0b" length:3],@"date":[NSDate dateWithTimeIntervalSince1970:1234],@"nested":@{@"key":@"value"}};
    CKKSCurrentItemQuery *query=[[CKKSCurrentItemQuery alloc]initWithIdentifier:@"标识" accessGroup:@"group" zoneID:@"区域"];
    CHECK([query.description isEqualToString:@"<CKKSCurrentItemQuery(区域-group): 标识>"]);
    CKKSCurrentItemQuery *q2=roundtrip(query);CHECK([q2.identifier isEqualToString:query.identifier]&&[q2.accessGroup isEqualToString:query.accessGroup]&&[q2.zoneID isEqualToString:query.zoneID]);
    CKKSCurrentItemQueryResult *result=[[CKKSCurrentItemQueryResult alloc]initWithIdentifier:@"标识" accessGroup:@"group" zoneID:@"区域" decryptedRecord:record];
    CHECK([result.description isEqualToString:@"<CKKSCurrentItemQueryResult(区域-group): 标识>"]);
    CKKSCurrentItemQueryResult *r2=roundtrip(result);CHECK([r2.decryptedRecord isEqual:record]&&[r2.identifier isEqual:result.identifier]);
    CKKSPCSIdentityQuery *pcs=[[CKKSPCSIdentityQuery alloc]initWithServiceNumber:@-7 accessGroup:@"group" publicKey:@"YWJj" zoneID:@"区域"];
    CHECK([pcs.description isEqualToString:@"<CKKSPCSIdentityQuery(区域): -7>"]);
    CKKSPCSIdentityQuery *p2=roundtrip(pcs);CHECK([p2.serviceNumber isEqual:pcs.serviceNumber]&&[p2.publicKey isEqual:pcs.publicKey]&&[p2.accessGroup isEqual:pcs.accessGroup]&&[p2.zoneID isEqual:pcs.zoneID]);
    CKKSPCSIdentityQueryResult *pr=[[CKKSPCSIdentityQueryResult alloc]initWithServiceNumber:@-7 publicKey:@"YWJj" zoneID:@"区域" decryptedRecord:record];
    CHECK([pr.description isEqualToString:@"<CKKSPCSIdentityQueryResult(区域): -7>"]);CKKSPCSIdentityQueryResult *pr2=roundtrip(pr);CHECK([pr2.decryptedRecord isEqual:record]&&[pr2.serviceNumber isEqual:pr.serviceNumber]&&[pr2.publicKey isEqual:pr.publicKey]&&[pr2.zoneID isEqual:pr.zoneID]);
    __weak NSMutableString *weakIdentifier;CKKSCurrentItemQuery *owner;
    @autoreleasepool{NSMutableString *text=[NSMutableString stringWithString:@"retained"];weakIdentifier=text;owner=[[CKKSCurrentItemQuery alloc]initWithIdentifier:text accessGroup:@"g" zoneID:@"z"];[text appendString:@"-mutated"];CHECK([owner.identifier isEqualToString:@"retained-mutated"]);}
    CHECK(weakIdentifier!=nil);owner.identifier=nil;CHECK(weakIdentifier==nil);
    owner.accessGroup=nil;owner.zoneID=nil;CKKSCurrentItemQuery *empty=roundtrip(owner);CHECK(empty.identifier==nil&&empty.accessGroup==nil&&empty.zoneID==nil);
    // Native Foundation accepts some inline plist primitives without an
    // instantiated-class check. Retain that observation separately; it does
    // not prove strict NSString field-type enforcement.
    query.identifier=(id)@42;NSError *primitiveError=nil;NSData *primitive=[NSKeyedArchiver archivedDataWithRootObject:query requiringSecureCoding:YES error:&primitiveError];CHECK(primitive);CKKSCurrentItemQuery *primitiveValue=[NSKeyedUnarchiver unarchivedObjectOfClass:[query class] fromData:primitive error:&primitiveError];
    printf("SECURE_ARCHIVE_NUMERIC_PRIMITIVE_OBSERVED accepted=%d error=%d\n",[primitiveValue.identifier isKindOfClass:[NSNumber class]],primitiveError!=nil);
    BOOL rejected=NO;@try{query.identifier=(id)[OOBUnexpectedValue new];NSError *error=nil;NSData *bad=[NSKeyedArchiver archivedDataWithRootObject:query requiringSecureCoding:YES error:&error];CHECK(bad);id value=[NSKeyedUnarchiver unarchivedObjectOfClass:[query class] fromData:bad error:&error];rejected=error!=nil||value==nil;}@catch(NSException *exception){rejected=YES;}CHECK(rejected&&unexpectedDecodes==0);
    printf("APPLE_SECURITY_OOB_VALUES_LAYOUT_RETAIN_SECURE_ARCHIVE_AND_REJECTION_OK checks=%u classes=4\n",checks);return 0;
}}
