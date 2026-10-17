#import <Foundation/Foundation.h>
#import <MobileAsset/MAAssetQuery.h>
#include <assert.h>
#include <dispatch/dispatch.h>
#include <dlfcn.h>
#include <mach/mach.h>
#include <objc/runtime.h>
#include <pthread.h>
#include <servers/bootstrap.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>
#include <uuid/uuid.h>
#include <xpc/xpc.h>
extern int xpc_pipe_receive(mach_port_t,xpc_object_t*,uint64_t);
extern int xpc_pipe_routine_reply(xpc_object_t);
static const char* service="com.apple.mobileassetd.v2";
static Class queryClass;
static unsigned checks;
#define CHECK(...) do { if (!(__VA_ARGS__)) { fprintf(stderr,"CHECK failed line %d: %s\n",__LINE__,#__VA_ARGS__); abort(); } __sync_add_and_fetch(&checks,1); } while(0)
static void waitDone(dispatch_semaphore_t done) { CHECK(!dispatch_semaphore_wait(done,dispatch_time(DISPATCH_TIME_NOW,15*NSEC_PER_SEC))); }
static MAAssetQuery* makeQuery(NSString* type) {
 MAAssetQuery* q=[[queryClass alloc] initWithType:type andPurpose:@"real-query-test"];
 CHECK(q && [q.assetType isEqual:type] && [q.purpose isEqual:@"real-query-test"]);
 CHECK(!q.isDone && q.resultCode==MAQueryUnknownResult && q.results==nil);
 CHECK([q returnTypes]==MACatalogOnly); [q returnTypes:MAInstalledOnly];
 q.doNotBlockBeforeFirstUnlock=YES; q.doNotBlockOnNetworkStatus=YES;
 CHECK([q addKeyValueArray:@"Flavor" with:@[@"A",@"B"]]==0);
 CHECK([q addKeyValueNull:@"Optional"]==0);
 CHECK([q addKeyValuePair:@"Name" with:@"snow-雪"]==0);
 CHECK([q addKeyValuePair:@"Invalid" with:(id)@1]==1);
 CHECK([q addKeyValueArray:@"Invalid" with:@[@1]]==1);
 CHECK([q addKeyValueArray:(id)@1 with:@[]]==1);
 CHECK([q.queryParams count]==3);
 return q;
}
static void checkResult(MAAssetQuery* q, NSInteger index, MAQueryResult result, NSError* error) {
 MAQueryResult expected=index==2?MAQueryCatalogNotDownloaded:index==3?MAQueryNotEntitled:
   index==4?MAQueryUnknownResult:index==5?MAQueryCouldNotEncodeResults:index==6?MAQueryHasAllowedDifferences:MAQuerySuccessful;
 CHECK(result==expected && q.resultCode==expected && q.isDone);
 BOOL failure=index==3||index==4||index==5;
 CHECK((error!=nil)==failure);
 if(error) CHECK([error.domain isEqual:@"com.apple.MobileAssetError.Query"] && error.code==expected);
 if(failure||index==2) { CHECK(q.results==nil && q.assetIds==nil);return; }
 CHECK([q.results count]==(index==1?0:1));
 CHECK([q.assetIds count]==[q.results count]);
 CHECK([q.postedDate timeIntervalSince1970]==12345 && [q.lastFetchDate timeIntervalSince1970]==12346);
 CHECK([q isCatalogFetchedFromLiveServer]);
 if(index!=1) {
  MAAsset* asset=[q.results objectAtIndex:0];
  CHECK([asset.assetType isEqual:q.assetType] && [asset.assetId isEqual:@"actual-fixture-asset"]);
  CHECK(asset.state==MAInstalled && [asset.attributes[@"Name"] isEqual:@"snow-雪"]);
  CHECK([asset.purpose isEqual:@"real-query-test"] && [q.assetIds containsObject:asset.assetId]);
 }
}
static void doCase(NSString* type,unsigned index,BOOL async) {
 @autoreleasepool {
  MAAssetQuery* q=makeQuery(type);
  if(async) {
   dispatch_semaphore_t done=dispatch_semaphore_create(0);
   [q queryMetaDataWithError:^(MAQueryResult code,NSError* error){checkResult(q,index,code,error);dispatch_semaphore_signal(done);}];
   waitDone(done);dispatch_release(done);
  } else {
   MAQueryResult code=[q queryMetaDataSync];
   NSError* e=(index==3||index==4||index==5)?[NSError errorWithDomain:@"com.apple.MobileAssetError.Query" code:code userInfo:nil]:nil;
   checkResult(q,index,code,e);
  }
  [q release];
 }
}
static void* worker(void* arg) {
 unsigned thread=(unsigned)(uintptr_t)arg;
 for(unsigned j=0;j<8;j++)doCase([NSString stringWithFormat:@"org.linuxcode.query.thread.%u.%u",thread,j],0,YES);
 return NULL;
}
static void client(void) {
 for(unsigned i=0;i<8;i++) doCase([NSString stringWithFormat:@"org.linuxcode.query.case.%u",i],i,i%2);
 pthread_t threads[4];for(unsigned t=0;t<4;t++)CHECK(!pthread_create(&threads[t],NULL,worker,(void*)(uintptr_t)t));
 for(unsigned t=0;t<4;t++)CHECK(!pthread_join(threads[t],NULL));
 // Release the query and leave its creator's autorelease pool before callback.
 dispatch_semaphore_t done=dispatch_semaphore_create(0); __block unsigned replies=0;
 for(unsigned i=0;i<8;i++) { @autoreleasepool {
  MAAssetQuery* q=makeQuery([NSString stringWithFormat:@"org.linuxcode.query.detached.%u",i]);
  [q queryMetaData:^(MAQueryResult code){CHECK(code==0);__sync_add_and_fetch(&replies,1);dispatch_semaphore_signal(done);}];[q release];
 }}
 for(unsigned i=0;i<8;i++)waitDone(done);CHECK(replies==8);dispatch_release(done);
 printf("MOBILEASSET_QUERY_REAL_48_XPC_REPLIES_4_THREADS_32_ASYNC_QUERIES_8_DETACHED_CALLBACKS_OK checks=%u\n",checks);
}
struct checkin { mach_msg_header_t header; mach_msg_body_t body; mach_msg_port_descriptor_t receive,send; };
int main(int argc,char**argv) {
 setbuf(stdout,NULL);@autoreleasepool {
 queryClass=objc_getClass("MAAssetQuery");CHECK(queryClass);
 Method method=class_getInstanceMethod(queryClass,@selector(queryMetaDataWithError:));Dl_info owner;CHECK(method && dladdr((void*)method_getImplementation(method),&owner));
 CHECK(strstr(owner.dli_fname,"mobileasset-query-source/frameworks/MobileAsset.framework"));
 if(argc==2 && !strcmp(argv[1],"--client")){client();return 0;}
 mach_port_t existing;CHECK(bootstrap_look_up(bootstrap_port,(char*)service,&existing)==BOOTSTRAP_UNKNOWN_SERVICE);
 MAAssetQuery* absent=makeQuery(@"org.linuxcode.query.absent");CHECK([absent queryMetaDataSync]==MAQueryXpcError && absent.isDone && absent.results==nil);
 dispatch_semaphore_t done=dispatch_semaphore_create(0);__block unsigned calls=0;
 [absent queryMetaDataWithError:^(MAQueryResult code,NSError* error){CHECK(code==MAQueryXpcError && [error.domain isEqual:@"com.apple.MobileAssetError.Query"] && error.code==1);calls++;dispatch_semaphore_signal(done);}];
 waitDone(done);CHECK(calls==1);[absent release];dispatch_release(done);
 MAAssetQuery* invalid=[[queryClass alloc]initWithType:nil];CHECK([invalid queryMetaDataSync]==MAQueryNilAssetType && invalid.isDone);[invalid release];
 CHECK(![queryClass instancesRespondToSelector:NSSelectorFromString(@"unimplementedUnknownQueryMethod")]);
 puts("MOBILEASSET_QUERY_REAL_ABSENT_SERVICE_SYNC_ASYNC_TYPED_ERRORS_NO_FAKE_SUCCESS_OK");
 mach_port_t receiver;CHECK(!mach_port_allocate(mach_task_self(),MACH_PORT_RIGHT_RECEIVE,&receiver));
 CHECK(!mach_port_insert_right(mach_task_self(),receiver,receiver,MACH_MSG_TYPE_MAKE_SEND));CHECK(!bootstrap_register(bootstrap_port,(char*)service,receiver));
 pid_t child=fork();CHECK(child>=0);if(!child){execl(argv[0],argv[0],"--client",NULL);_exit(127);}
 for(unsigned n=0;n<48;n++) { @autoreleasepool {
  union {struct checkin checkin;unsigned char bytes[512];} message={0};
  CHECK(!mach_msg(&message.checkin.header,MACH_RCV_MSG|MACH_RCV_TIMEOUT,0,sizeof(message),receiver,15000,MACH_PORT_NULL));
  CHECK(message.checkin.header.msgh_id==0x77303074 && message.checkin.body.msgh_descriptor_count==2);
  mach_port_t transport=message.checkin.receive.name;xpc_object_t request=NULL;CHECK(!xpc_pipe_receive(transport,&request,0)&&request);
  CHECK(xpc_get_type(xpc_dictionary_get_value(request,"messageAction"))==XPC_TYPE_INT64 && xpc_dictionary_get_int64(request,"messageAction")==1);
  CHECK(xpc_dictionary_get_int64(request,"returnAssetTypes")==1);
  CHECK(xpc_dictionary_get_bool(request,"doNotBlockBeforeFirstUnlock") && xpc_dictionary_get_bool(request,"doNotBlockOnNetworkStatus"));
  CHECK(!strcmp(xpc_dictionary_get_string(request,"Purpose"),"real-query-test"));
  CHECK(!strcmp(xpc_dictionary_get_string(request,"requestType"),"requestTypeSync"));
  uuid_t uuid;CHECK(!uuid_parse(xpc_dictionary_get_string(request,"connectionIdentifier"),uuid));
  const char* asset=xpc_dictionary_get_string(request,"AssetType");CHECK(asset);
  unsigned index=0;if(strstr(asset,".case."))CHECK(sscanf(asset,"org.linuxcode.query.case.%u",&index)==1);
  size_t length=0;const void* bytes=xpc_dictionary_get_data(request,"QueryParams",&length);CHECK(bytes && length);
  NSError* error=nil;NSSet* allowed=[NSSet setWithObjects:[NSArray class],[NSDictionary class],[NSString class],[NSNull class],nil];
  NSArray* params=[NSKeyedUnarchiver unarchivedObjectOfClasses:allowed fromData:[NSData dataWithBytes:bytes length:length] error:&error];
  CHECK(!error && [params count]==3 && [params[0][@"queryKey"] isEqual:@"Flavor"]);
  CHECK([params[0][@"queryValue"] isEqual:@[@"A",@"B"]] && [params[1][@"queryValue"] isEqual:@[[NSNull null]]]);
  CHECK([params[2][@"queryValue"] isEqual:@[@"snow-雪"]]);
  xpc_object_t reply=xpc_dictionary_create_reply(request);CHECK(reply);
  NSInteger code=index==2?2:index==3?5:index==6?14:0;xpc_dictionary_set_int64(reply,"Result",code);
  if(index==4)xpc_dictionary_set_string(reply,"Result","wrong-type");
  if(index!=2 && index!=3 && index!=4) {
   NSArray* assets=index==1?@[]:@[@{@"AssetProperties":@{@"Name":@"snow-雪",@"AssetPurpose":@"real-query-test"},@"AssetAddedProperties":@{@"AssetState":@2,@"AssetType":[NSString stringWithUTF8String:asset],@"AssetId":@"actual-fixture-asset"}}];
   NSDictionary* payload=@{@"assetsToFrameWork":assets,@"metaToFrameWork":@{@"postedDate":[NSDate dateWithTimeIntervalSince1970:12345],@"lastTimeChecked":[NSDate dateWithTimeIntervalSince1970:12346]},@"catalogInfoToFrameWork":@{@"isLiveServer":@YES}};
   NSData* data=[NSKeyedArchiver archivedDataWithRootObject:payload requiringSecureCoding:YES error:&error];CHECK(data&&!error);
   if(index==5)xpc_dictionary_set_data(reply,"xmlData","malformed",9);
   else xpc_dictionary_set_data(reply,"xmlData",[data bytes],[data length]);
  }
  CHECK(!xpc_pipe_routine_reply(reply));xpc_release(reply);xpc_release(request);
  CHECK(!mach_port_destroy(mach_task_self(),transport));CHECK(!mach_port_deallocate(mach_task_self(),message.checkin.send.name));
 }}
 int status;CHECK(waitpid(child,&status,0)==child && WIFEXITED(status)&&!WEXITSTATUS(status));
 CHECK(!mach_port_destroy(mach_task_self(),receiver));
 printf("MOBILEASSET_QUERY_PROTOCOL_KEYED_FILTERS_RESULTS_METADATA_ERRORS_48_REAL_REQUESTS_OK checks=%u\n",checks);
 }return 0;
}
