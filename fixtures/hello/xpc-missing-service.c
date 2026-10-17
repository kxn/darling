#include <xpc/xpc.h>
#include <dispatch/dispatch.h>
#include <servers/bootstrap.h>
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
static atomic_int events,async_invalid,sync_invalid;
int main(void) {
 setbuf(stdout,NULL);char names[2][128];xpc_connection_t connections[2];dispatch_semaphore_t done=dispatch_semaphore_create(0);
 for(unsigned i=0;i<2;i++) {
  snprintf(names[i],sizeof(names[i]),"org.linuxcode.absent-xpc.%d.%u",getpid(),i);
  mach_port_t port=0;int status=bootstrap_look_up(bootstrap_port,names[i],&port);
  printf("XPC_MISSING_LOOKUP index=%u status=%d port=%u\n",i,status,port);
  if(status!=BOOTSTRAP_UNKNOWN_SERVICE)return 3;
  connections[i]=xpc_connection_create_mach_service(names[i],dispatch_get_global_queue(0,0),0);
  if(!connections[i])return 4;
  xpc_connection_set_event_handler(connections[i],^(xpc_object_t value){if(value==XPC_ERROR_CONNECTION_INVALID)atomic_fetch_add(&events,1);});
  xpc_connection_resume(connections[i]);
 }
 xpc_object_t request=xpc_dictionary_create(NULL,NULL,0);
 xpc_connection_send_message_with_reply(connections[0],request,dispatch_get_global_queue(0,0),^(xpc_object_t reply){printf("XPC_MISSING_ASYNC_REPLY invalid=%d\n",reply==XPC_ERROR_CONNECTION_INVALID);if(reply==XPC_ERROR_CONNECTION_INVALID)atomic_store(&async_invalid,1);dispatch_semaphore_signal(done);});
 xpc_connection_t sync_connection=connections[1];
 dispatch_async(dispatch_get_global_queue(0,0),^{xpc_object_t reply=xpc_connection_send_message_with_reply_sync(sync_connection,request);printf("XPC_MISSING_SYNC_REPLY invalid=%d\n",reply==XPC_ERROR_CONNECTION_INVALID);if(reply==XPC_ERROR_CONNECTION_INVALID)atomic_store(&sync_invalid,1);if(reply)xpc_release(reply);dispatch_semaphore_signal(done);});
 int timeouts=0;for(unsigned i=0;i<2;i++)if(dispatch_semaphore_wait(done,dispatch_time(DISPATCH_TIME_NOW,3*NSEC_PER_SEC)))timeouts++;
 usleep(200000);int verified=!timeouts && atomic_load(&events)==2 && atomic_load(&async_invalid) && atomic_load(&sync_invalid);
 printf("XPC_MISSING_RESULT verified=%d events=%d async=%d sync=%d timeouts=%d\n",verified,atomic_load(&events),atomic_load(&async_invalid),atomic_load(&sync_invalid),timeouts);
 // A failing baseline may still have a blocked synchronous sender. Terminate
 // the isolated test process rather than waiting for that worker to return.
 _exit(verified?0:2);
}
