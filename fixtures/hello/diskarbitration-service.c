#include <DiskArbitration/DiskArbitration.h>
#include <CoreFoundation/CoreFoundation.h>
#include <mach/mach.h>
#include <servers/bootstrap.h>
#include <dlfcn.h>
#include <stdio.h>
#include <unistd.h>
#include <errno.h>
static unsigned appeared;
static void disk_appeared(DADiskRef disk,void* context) {
    (void)context;appeared++;
    CFDictionaryRef description=DADiskCopyDescription(disk);
    printf("DA_APPEARED disk=%p bsd=%s description=%p\n",disk,DADiskGetBSDName(disk),description);
    if(description) CFRelease(description);
}
int main(void) {
    setbuf(stdout,NULL);
    Dl_info owner={0};dladdr((void*)DASessionCreate,&owner);
    printf("DA_OWNER %s\n",owner.dli_fname);
    mach_port_t service=MACH_PORT_NULL;
    kern_return_t status=bootstrap_look_up(bootstrap_port,"com.apple.DiskArbitration.diskarbitrationd",&service);
    printf("DA_BOOTSTRAP status=%d port=%u\n",status,service);
    if(service) mach_port_deallocate(mach_task_self(),service);
    errno=0;DASessionRef session=DASessionCreate(kCFAllocatorDefault);
    printf("DA_SESSION %p errno=%d type=%lu\n",session,errno,(unsigned long)DASessionGetTypeID());
    if(!session) {puts("DA_PROBE_RETURNED session=0");return 0;}
    for(const char** p=(const char*[]){"/","/Volumes/SystemRoot/",NULL};*p;p++) {
        CFURLRef url=CFURLCreateFromFileSystemRepresentation(NULL,(const UInt8*)*p,__builtin_strlen(*p),true);
        DADiskRef disk=DADiskCreateFromVolumePath(NULL,session,url);
        CFDictionaryRef description=disk?DADiskCopyDescription(disk):NULL;
        printf("DA_VOLUME path=%s disk=%p description=%p\n",*p,disk,description);
        if(description) {CFShow(description);CFRelease(description);}
        if(disk) CFRelease(disk);CFRelease(url);
    }
    DARegisterDiskAppearedCallback(session,NULL,disk_appeared,NULL);
    DASessionScheduleWithRunLoop(session,CFRunLoopGetCurrent(),kCFRunLoopDefaultMode);
    for(unsigned i=0;i<6;i++) CFRunLoopRunInMode(kCFRunLoopDefaultMode,.5,false);
    DASessionUnscheduleFromRunLoop(session,CFRunLoopGetCurrent(),kCFRunLoopDefaultMode);
    printf("DA_PROBE_RETURNED session=1 appeared=%u\n",appeared);CFRelease(session);return 0;
}
