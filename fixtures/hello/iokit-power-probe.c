#include <IOKit/IOKitLib.h>
#include <IOKit/pwr_mgt/IOPMLib.h>
#include <mach/mach.h>
#include <stdio.h>
static void power(void* context,io_service_t service,natural_t message,void* argument) {(void)context;(void)service;(void)message;(void)argument;}
int main(void) {
    setbuf(stdout,NULL);mach_port_t master=0;kern_return_t error=IOMainPort(MACH_PORT_NULL,&master);
    printf("IOPOWER_MASTER status=%d port=%u\n",error,master);
    io_registry_entry_t root=IORegistryEntryFromPath(master,"IOPower:/IOPowerConnection/IOPMrootDomain");
    printf("IOPOWER_ROOT_DOMAIN object=%u\n",root);
    IONotificationPortRef port=IONotificationPortCreate(master);mach_port_type_t kind=0;
    error=port?mach_port_type(mach_task_self(),IONotificationPortGetMachPort(port),&kind):KERN_INVALID_ARGUMENT;
    printf("IOPOWER_NOTIFICATION_PORT present=%d status=%d type=%u\n",port!=NULL,error,kind);
    if(port)IONotificationPortDestroy(port);
    port=NULL;io_object_t notifier=0;io_connect_t connection=IORegisterForSystemPower(NULL,&port,power,&notifier);
    printf("IOPOWER_REGISTRATION connection=%u notifier=%u port=%p\n",connection,notifier,port);
    if(notifier)IODeregisterForSystemPower(&notifier);if(connection)IOServiceClose(connection);if(port)IONotificationPortDestroy(port);
    if(root)IOObjectRelease(root);if(master)mach_port_deallocate(mach_task_self(),master);
    puts("IOPOWER_PROBE_RETURNED");return 0;
}
