#include <CoreFoundation/CoreFoundation.h>
#include <IOKit/IOKitLib.h>
#include <IOKit/IOCFSerialize.h>
#include <mach/mach.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
extern uint64_t matching_fixture_create(int);
extern void matching_fixture_republish(int);
extern void matching_fixture_remove(int);
extern kern_return_t io_service_add_notification_64(mach_port_t,char*,char*,mach_port_t,uint64_t*,uint32_t,mach_port_t*);
extern kern_return_t io_service_add_notification_bin_64(mach_port_t,char*,char*,uint32_t,mach_port_t,uint64_t*,uint32_t,mach_port_t*);
static unsigned checks,callbacks;
#define check(c) do {++checks;if(!(c)){fprintf(stderr,"MATCHING_FAIL line=%d check=%u\n",__LINE__,checks);exit(1);}}while(0)
static io_iterator_t callback_iterator;
static void callback(void* context,io_iterator_t iterator){check(context==(void*)0x123456789ULL);callback_iterator=iterator;++callbacks;}
static void receive(IONotificationPortRef port,int expected) {
 union {mach_msg_header_t h;unsigned char buffer[512];} m;
 kern_return_t result=mach_msg(&m.h,MACH_RCV_MSG|MACH_RCV_TIMEOUT,0,sizeof(m),IONotificationPortGetMachPort(port),expected?2000:30,0);
 if(!expected){check(result==MACH_RCV_TIMED_OUT);return;}
 check(result==0);check(m.h.msgh_id==53);check(m.h.msgh_size==56);
 IODispatchCalloutFromMessage(NULL,&m.h,port);
}
static unsigned drain(io_iterator_t iterator,uint64_t* last) {
 unsigned count=0;io_object_t service;
 while((service=IOIteratorNext(iterator))!=0){++count;check(!IORegistryEntryGetRegistryEntryID(service,last));IOObjectRelease(service);}
 return count;
}
static CFMutableDictionaryRef criteria(void){return IOServiceMatching("DarlingMatchingFixture");}
static io_iterator_t subscribe(IONotificationPortRef port,const char* type) {
 io_iterator_t iterator=0;check(!IOServiceAddMatchingNotification(port,type,criteria(),callback,(void*)0x123456789ULL,&iterator));check(iterator);return iterator;
}
static unsigned receivers(void) {
 mach_port_name_array_t names=NULL;mach_port_type_array_t types=NULL;mach_msg_type_number_t nc=0,tc=0;
 check(!mach_port_names(mach_task_self(),&names,&nc,&types,&tc));unsigned result=0;
 for(unsigned i=0;i<tc;i++)if(types[i]&MACH_PORT_TYPE_RECEIVE)++result;
 vm_deallocate(mach_task_self(),(vm_address_t)names,nc*sizeof(*names));vm_deallocate(mach_task_self(),(vm_address_t)types,tc*sizeof(*types));return result;
}
static void extra_paths(mach_port_t master) {
 uint64_t id=0;IONotificationPortRef port=IONotificationPortCreate(master);check(port);
 CFMutableDictionaryRef dict=criteria();char payload[6001];memset(payload,'q',6000);payload[6000]=0;
 CFStringRef text=CFStringCreateWithCString(NULL,payload,kCFStringEncodingUTF8);
 CFDictionaryRef properties=CFDictionaryCreate(NULL,(const void*[]){CFSTR("FixturePayload")},(const void*[]){text},1,&kCFTypeDictionaryKeyCallBacks,&kCFTypeDictionaryValueCallBacks);
 CFDictionarySetValue(dict,CFSTR("IOPropertyMatch"),properties);CFRelease(properties);CFRelease(text);
 io_iterator_t it=0;CFRetain(dict);check(!IOServiceAddMatchingNotification(port,kIOMatchedNotification,dict,callback,(void*)0x123456789ULL,&it));check(drain(it,&id)==4);
 uint64_t created=matching_fixture_create(99);receive(port,1);check(callback_iterator==it);check(drain(it,&id)==1&&id==created);
 io_iterator_t snapshot=0;check(!IOServiceGetMatchingServices(master,dict,&snapshot)); // consumes dict
 matching_fixture_remove(99);check(drain(snapshot,&id)==5);IOObjectRelease(snapshot);IOObjectRelease(it);IONotificationPortDestroy(port);
 puts("MATCHING_OOL_SUBSCRIPTION_AND_SNAPSHOT_LIFETIME_OK");
 // Explicit legacy XML64 and malformed-binary RPCs use the generated user stub.
 port=IONotificationPortCreate(master);dict=criteria();CFDataRef xml=IOCFSerialize(dict,0);CFRelease(dict);check(xml);
 char bytes[4096]={0};check(CFDataGetLength(xml)<sizeof(bytes));memcpy(bytes,CFDataGetBytePtr(xml),CFDataGetLength(xml));CFRelease(xml);
 uint64_t refs[8]={0,(uintptr_t)callback,0x123456789ULL};
 check(!io_service_add_notification_64(master,(char*)kIOMatchedNotification,bytes,IONotificationPortGetMachPort(port),refs,3,&it));check(drain(it,&id)==4);
 created=matching_fixture_create(98);receive(port,1);check(callback_iterator==it);check(drain(it,&id)==1&&id==created);matching_fixture_remove(98);
 IOObjectRelease(it);it=0;
 check(io_service_add_notification_bin_64(master,(char*)kIOMatchedNotification,"garbage",7,IONotificationPortGetMachPort(port),refs,3,&it)!=KERN_SUCCESS&&!it);
 check(io_service_add_notification_64(master,"unsupported-notification",bytes,IONotificationPortGetMachPort(port),refs,3,&it)==kIOReturnUnsupported&&!it);
 IONotificationPortDestroy(port);puts("MATCHING_XML64_AND_INVALID_REQUESTS_OK");
 // Force timeout/retry on the actual Mach queue, then confirm no leaked rights.
 for(unsigned deregister=0;deregister<2;deregister++) {
  port=IONotificationPortCreate(master);check(port);it=subscribe(port,kIOMatchedNotification);check(drain(it,&id)==4);
  mach_port_t wake=IONotificationPortGetMachPort(port);mach_port_limits_t limit={.mpl_qlimit=1};
  check(!mach_port_set_attributes(mach_task_self(),wake,MACH_PORT_LIMITS_INFO,(mach_port_info_t)&limit,MACH_PORT_LIMITS_INFO_COUNT));
  mach_msg_header_t dummy={0};dummy.msgh_bits=MACH_MSGH_BITS(MACH_MSG_TYPE_MAKE_SEND,0);dummy.msgh_remote_port=wake;dummy.msgh_id=999;dummy.msgh_size=sizeof(dummy);
  check(!mach_msg(&dummy,MACH_SEND_MSG|MACH_SEND_TIMEOUT,sizeof(dummy),0,0,0,0));
  created=matching_fixture_create(97);usleep(50000);
  mach_port_urefs_t refs_count=0;check(!mach_port_get_refs(mach_task_self(),it,MACH_PORT_RIGHT_SEND,&refs_count));check(refs_count==1);
  if(deregister) {
   check(!IOObjectRelease(it));
   mach_port_type_t kind=0;kern_return_t status=0;
   for(unsigned n=0;n<200;n++){status=mach_port_type(mach_task_self(),it,&kind);if(status==KERN_INVALID_NAME)break;usleep(10000);}
   check(status==KERN_INVALID_NAME);
  }
  union{mach_msg_header_t h;unsigned char storage[128];} message;
  check(!mach_msg(&message.h,MACH_RCV_MSG|MACH_RCV_TIMEOUT,0,sizeof(message),wake,1000,0));check(message.h.msgh_id==999);
  if(!deregister){receive(port,1);check(callback_iterator==it);check(drain(it,&id)==1&&id==created);IOObjectRelease(it);}
  else receive(port,0);
  matching_fixture_remove(97);IONotificationPortDestroy(port);
 }
 puts("MATCHING_FULL_QUEUE_RETRY_AND_DEREGISTRATION_OK");
}
void matching_client(mach_port_t master) {
 IONotificationPortRef port=IONotificationPortCreate(master);check(port);
 io_iterator_t publish=subscribe(port,kIOPublishNotification),first=subscribe(port,kIOFirstMatchNotification),terminated=subscribe(port,kIOTerminatedNotification);
 uint64_t id=0;check(drain(publish,&id)==1);uint64_t initial=id;check(drain(first,&id)==1&&id==initial);check(drain(terminated,&id)==0);
 receive(port,0); // Registration queues the initial set without an asynchronous ping.
 uint64_t second=matching_fixture_create(2);
 receive(port,1);check(callback_iterator==publish||callback_iterator==first);
 receive(port,1);receive(port,0);check(callbacks==2);
 check(drain(publish,&id)==1&&id==second);check(drain(first,&id)==1&&id==second);
 matching_fixture_republish(2);receive(port,1);check(callback_iterator==publish);receive(port,0);
 check(drain(publish,&id)==1&&id==second);check(drain(first,&id)==0);
 // Two new services coalesce into one ping per subscription until fully drained.
 uint64_t third=matching_fixture_create(3);uint64_t fourth=matching_fixture_create(4);
 receive(port,1);receive(port,1);receive(port,0);
 check(drain(publish,&id)==2&&id==third);check(drain(first,&id)==2&&id==third);
 (void)fourth;
 // Matching queries and property predicates must agree with actual registry objects.
 io_service_t found=IOServiceGetMatchingService(master,IORegistryEntryIDMatching(second));check(found);
 check(!IORegistryEntryGetRegistryEntryID(found,&id)&&id==second);
 CFMutableDictionaryRef match=criteria();int label=2;CFNumberRef number=CFNumberCreate(NULL,kCFNumberIntType,&label);
 CFDictionaryRef property=CFDictionaryCreate(NULL,(const void*[]){CFSTR("FixtureLabel")},(const void*[]){number},1,&kCFTypeDictionaryKeyCallBacks,&kCFTypeDictionaryValueCallBacks);
 CFDictionarySetValue(match,CFSTR("IOPropertyMatch"),property);CFRelease(property);CFRelease(number);
 boolean_t matches=0;check(!IOServiceMatchPropertyTable(found,match,&matches)&&matches);CFRelease(match);
 IOObjectRelease(found);
 found=IOServiceGetMatchingService(master,IOServiceNameMatching("Fixture-2"));check(found);IOObjectRelease(found);
 found=IOServiceGetMatchingService(master,IOServiceMatching("IOService"));check(found);IOObjectRelease(found);
 // The termination queue keeps an object alive after its provider unregisters it.
 matching_fixture_remove(2);receive(port,1);check(callback_iterator==terminated);receive(port,0);
 check(drain(terminated,&id)==1&&id==second);check(!IOServiceGetMatchingService(master,IORegistryEntryIDMatching(second)));
 IOIteratorReset(terminated);check(drain(terminated,&id)==0);
 // Dropping a notifier suppresses an already queued callback in the native client.
 io_iterator_t dropped=subscribe(port,kIOMatchedNotification);check(drain(dropped,&id)==3);
 matching_fixture_create(5);check(!IOObjectRelease(dropped));
 // publish, first and dropped each queued a message. Only the first two survive.
 unsigned before=callbacks;receive(port,1);receive(port,1);receive(port,1);check(callbacks==before+2);
 check(drain(publish,&id)==1);check(drain(first,&id)==1);
 check(!IOObjectRelease(publish));check(!IOObjectRelease(first));check(!IOObjectRelease(terminated));IONotificationPortDestroy(port);
 extra_paths(master);usleep(100000);unsigned baseline=receivers();
 io_iterator_t retired[128]={0};
 for(unsigned i=0;i<128;i++) {
  port=IONotificationPortCreate(master);check(port);io_iterator_t it=subscribe(port,kIOFirstPublishNotification);check(drain(it,&id)==4);retired[i]=it;
  check(!IOObjectRelease(it));IONotificationPortDestroy(port);
 }
 unsigned final=0;unsigned pending=128;
 for(unsigned retry=0;retry<200;retry++) {
  pending=0;
  for(unsigned i=0;i<128;i++){mach_port_type_t type=0;kern_return_t e=mach_port_type(mach_task_self(),retired[i],&type);if(e==0&&(type&MACH_PORT_TYPE_RECEIVE))++pending;}
  if(!pending)break;usleep(10000);
 }
 check(!pending);final=receivers();
 printf("MATCHING_PORTS baseline=%u final=%u cycles=128\n",baseline,final);check(final<=baseline);
 puts("MATCHING_128_RETIRED_MACH_RECEIVE_PORTS_DESTROYED");
 printf("IOKIT_MATCHING_NATIVE_CALLBACKS_OK checks=%u callbacks=%u cycles=128\n",checks,callbacks);
}
