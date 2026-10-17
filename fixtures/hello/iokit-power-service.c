#include <IOKit/IOKitLib.h>
#include <CoreFoundation/CoreFoundation.h>
#include <IOKit/pwr_mgt/IOPMLib.h>
#include <mach/mach.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static unsigned checks;
#define check(c) do { ++checks; if(!(c)) {fprintf(stderr,"POWER_FAIL line=%d check=%u\n",__LINE__,checks);exit(1);} } while(0)
static void power(void* c,io_service_t s,natural_t m,void* a) {(void)c;(void)s;(void)m;(void)a;}
static void physical_ool(void) {
 const unsigned sizes[]={0,1,4095,8191,8192,8193,65537};
 mach_port_t receive=0;check(!mach_port_allocate(mach_task_self(),MACH_PORT_RIGHT_RECEIVE,&receive));
 check(!mach_port_insert_right(mach_task_self(),receive,receive,MACH_MSG_TYPE_MAKE_SEND));
 for(unsigned n=0;n<sizeof(sizes)/sizeof(*sizes);n++) {
  unsigned size=sizes[n];unsigned char* bytes=malloc(size?size:1);check(bytes);memset(bytes,0x39,size);
#pragma pack(push,4)
  struct Packet {mach_msg_header_t head;mach_msg_body_t body;mach_msg_port_descriptor_t task;mach_msg_ool_descriptor_t data;unsigned marker;};
#pragma pack(pop)
  union {struct Packet p;unsigned char buffer[512];} message={0};
  struct Packet* p=&message.p;
  p->head.msgh_bits=MACH_MSGH_BITS_COMPLEX|MACH_MSGH_BITS(MACH_MSG_TYPE_COPY_SEND,0);
  p->head.msgh_remote_port=receive;p->head.msgh_id=0x1345;p->head.msgh_size=sizeof(*p);
  p->body.msgh_descriptor_count=2;p->task.name=mach_task_self();p->task.disposition=MACH_MSG_TYPE_COPY_SEND;p->task.type=MACH_MSG_PORT_DESCRIPTOR;
  p->data.address=size?bytes:NULL;p->data.size=size;p->data.type=MACH_MSG_OOL_DESCRIPTOR;p->data.copy=MACH_MSG_PHYSICAL_COPY;p->marker=0x13371337;
  check(!mach_msg(&p->head,MACH_SEND_MSG,sizeof(*p),0,0,0,0));
  memset(bytes,0x75,size);
  check(!mach_msg(&p->head,MACH_RCV_MSG|MACH_RCV_TIMEOUT,0,sizeof(message),receive,2000,0));
  check(p->head.msgh_id==0x1345 && p->body.msgh_descriptor_count==2 && p->marker==0x13371337);
  int pid=-1;check(!pid_for_task(p->task.name,&pid)&&pid==getpid());
  check(p->data.size==size && p->data.type==MACH_MSG_OOL_DESCRIPTOR);
  if(size) {unsigned char* b=p->data.address;for(unsigned i=0;i<size;i++)check(b[i]==0x39);}
  else check(p->data.address==NULL);
  mach_msg_destroy(&p->head);free(bytes);
 }
 check(!mach_port_destroy(mach_task_self(),receive));
 puts("POWER_MIXED_PORT_PHYSICAL_OOL_COPY_OK cases=7");
}
static unsigned receive_count(task_t task) {
 mach_port_name_array_t names=NULL;mach_port_type_array_t types=NULL;mach_msg_type_number_t nc=0,tc=0;
 check(!mach_port_names(task,&names,&nc,&types,&tc));check(nc==tc);unsigned count=0;
 for(unsigned i=0;i<tc;i++)if(types[i]&MACH_PORT_TYPE_RECEIVE)++count;
 static int printed=0;
 if(count>200&&!printed++)for(unsigned i=0,shown=0;i<nc&&shown<8;i++)if(types[i]&MACH_PORT_TYPE_RECEIVE){
  mach_port_status_t st={0};mach_msg_type_number_t size=MACH_PORT_RECEIVE_STATUS_COUNT;mach_port_urefs_t refs=0;
  kern_return_t a=mach_port_get_attributes(task,names[i],MACH_PORT_RECEIVE_STATUS,(mach_port_info_t)&st,&size);
  kern_return_t b=mach_port_get_refs(task,names[i],MACH_PORT_RIGHT_SEND,&refs);
  printf("PORT_DIAG name=%u types=%u status=%u rights=%u mscount=%u queued=%u refs_status=%u refs=%u\n",names[i],types[i],a,st.mps_srights,st.mps_mscount,st.mps_msgcount,b,refs);++shown;
 }
 check(!vm_deallocate(mach_task_self(),(vm_address_t)names,nc*sizeof(*names)));
 check(!vm_deallocate(mach_task_self(),(vm_address_t)types,tc*sizeof(*types)));
 return count;
}
int main(void) {
 setbuf(stdout,NULL);physical_ool();mach_port_t master=0;check(!IOMainPort(0,&master));
 io_service_t root=IORegistryEntryFromPath(master,"IOPower:/IOPowerConnection/IOPMrootDomain");check(root);
 check(IOObjectConformsTo(root,"IOPMrootDomain"));check(IOObjectConformsTo(root,"IOService"));check(IOObjectConformsTo(root,"IORegistryEntry"));
 CFTypeRef support=IORegistryEntryCreateCFProperty(root,CFSTR("DarlingPowerObservesResume"),kCFAllocatorDefault,0);
 check(support&&CFEqual(support,kCFBooleanTrue));CFRelease(support);
 support=IORegistryEntryCreateCFProperty(root,CFSTR("DarlingPowerSupportsSleepBarrier"),kCFAllocatorDefault,0);
 check(support&&CFEqual(support,kCFBooleanFalse));CFRelease(support);
 check(IORegistryEntryCreateCFProperty(root,CFSTR("DarlingMissingProperty"),kCFAllocatorDefault,0)==NULL);
 CFMutableDictionaryRef props=NULL;check(!IORegistryEntryCreateCFProperties(root,&props,kCFAllocatorDefault,0));
 check(props&&CFGetTypeID(props)==CFDictionaryGetTypeID()&&CFDictionaryGetCount(props)==4);CFRelease(props);
 // Obtain only this test's Darling daemon task, to observe actual receive-port
 // lifetime independently of the registry and its object-count implementation.
 FILE* job=popen("/bin/launchctl list org.darlinghq.iokitd","r");check(job);char line[1024];int daemon_pid=0;
 while(fgets(line,sizeof(line),job)) {char* at=strstr(line,"\"PID\"");if(at){at=strchr(at,'=');if(at)daemon_pid=atoi(at+1);}}
 check(pclose(job)==0);check(daemon_pid>0);task_t daemon=0;check(!task_for_pid(mach_task_self(),daemon_pid,&daemon));
 unsigned baseline=receive_count(daemon);
 io_connect_t bad=0;check(IOServiceOpen(root,mach_task_self(),1,&bad)!=KERN_SUCCESS&&bad==0);
 check(IOServiceOpen(root,daemon,0,&bad)==kIOReturnNotPermitted&&bad==0);
 check(IOServiceOpen(master,mach_task_self(),0,&bad)!=KERN_SUCCESS&&bad==0);
 for(unsigned i=0;i<128;i++) {
  io_connect_t conn=0;kern_return_t e=IOServiceOpen(root,mach_task_self(),0,&conn);check(e==0&&conn);
  io_service_t service=0;check(!IOConnectGetService(conn,&service));check(IOObjectIsEqualTo(service,root));IOObjectRelease(service);
  uint32_t out=0;check(IOConnectCallScalarMethod(conn,0x7fffffff,NULL,0,NULL,&out)!=KERN_SUCCESS);
  IONotificationPortRef port=IONotificationPortCreate(master);check(port);io_object_t notify=0;
  e=IOServiceAddInterestNotification(port,root,kIOAppPowerStateInterest,power,NULL,&notify);check(e==0&&notify);
  if(i==0) {unsigned active=receive_count(daemon);printf("POWER_PORTS baseline=%u active=%u\n",baseline,active);check(active>=baseline+2);}
  io_object_t invalid=0;check(IOServiceAddInterestNotification(port,root,kIOAppPowerStateInterest,NULL,NULL,&invalid)==kIOReturnBadArgument&&!invalid);
  check(!IOObjectRelease(notify));IONotificationPortDestroy(port);
  check(!IOObjectRetain(conn));check(!IOServiceClose(conn));
  service=0;check(IOConnectGetService(conn,&service)==kIOReturnNotOpen&&!service);check(!IOObjectRelease(conn));
 }
 unsigned final=~0u;
 for(unsigned retry=0;retry<200;retry++){final=receive_count(daemon);if(final==baseline)break;usleep(10000);}
 printf("POWER_PORTS baseline=%u final=%u cycles=128\n",baseline,final);check(final==baseline);
 // The unchanged public convenience API must produce all three live objects.
 IONotificationPortRef port=NULL;io_object_t notifier=0;io_connect_t conn=IORegisterForSystemPower(NULL,&port,power,&notifier);
 check(conn&&port&&notifier);check(!IODeregisterForSystemPower(&notifier));check(!IOServiceClose(conn));IONotificationPortDestroy(port);
 mach_port_deallocate(mach_task_self(),daemon);IOObjectRelease(root);mach_port_deallocate(mach_task_self(),master);
 printf("IOKIT_POWER_SERVICE_OK checks=%u cycles=128 physical_ool_cases=7\n",checks);return 0;
}
