#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <servers/bootstrap.h>
#include <dispatch/dispatch.h>
#include <sys/wait.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
struct capability {mach_msg_header_t h;mach_msg_body_t body;mach_msg_port_descriptor_t task;};
union incoming {struct capability cap;char bytes[1024];};
static void receive(mach_port_t port,union incoming* msg) {
 memset(msg,0,sizeof(*msg));assert(!mach_msg(&msg->cap.h,MACH_RCV_MSG|MACH_RCV_TIMEOUT,0,sizeof(*msg),port,25000,0));
}
static void header(mach_port_t remote,mach_port_t local,int id,unsigned disposition) {
 mach_msg_header_t h={0};h.msgh_bits=MACH_MSGH_BITS(disposition,local?MACH_MSG_TYPE_MAKE_SEND_ONCE:0);h.msgh_remote_port=remote;h.msgh_local_port=local;h.msgh_id=id;
 assert(!mach_msg(&h,MACH_SEND_MSG,sizeof(h),0,0,0,0));
}
int main(void) {
 setbuf(stdout,NULL);mach_port_t port;assert(!mach_port_allocate(mach_task_self(),MACH_PORT_RIGHT_RECEIVE,&port));assert(!mach_port_insert_right(mach_task_self(),port,port,MACH_MSG_TYPE_MAKE_SEND));
 char service[128];snprintf(service,sizeof(service),"org.linuxcode.remote-vm-map-%d",getpid());assert(!bootstrap_register(bootstrap_port,service,port));
 int pipefd[2];assert(!pipe(pipefd));pid_t child=fork();assert(child>=0);
 if(!child) {
  close(pipefd[1]);char ready;assert(read(pipefd[0],&ready,1)==1);close(pipefd[0]);
  mach_port_t server,reply;assert(!bootstrap_look_up(bootstrap_port,service,&server));assert(!mach_port_allocate(mach_task_self(),MACH_PORT_RIGHT_RECEIVE,&reply));
  header(server,reply,1,MACH_MSG_TYPE_COPY_SEND);union incoming input;receive(reply,&input);assert(input.cap.h.msgh_id==2);mach_port_t target=input.cap.task.name;
  mach_vm_address_t original=0;assert(!mach_vm_allocate(mach_task_self(),&original,4096,VM_FLAGS_ANYWHERE));memset((void*)original,0x47,4096);
  memory_object_size_t size=4096;mach_port_t entry=0;assert(!mach_make_memory_entry_64(mach_task_self(),&size,original,VM_PROT_READ|VM_PROT_WRITE,&entry,0));
  puts("REMOTE_VM_MAP_CALL");mach_vm_address_t remote=0;kern_return_t result=mach_vm_map(target,&remote,4096,0,VM_FLAGS_ANYWHERE,entry,0,FALSE,VM_PROT_READ|VM_PROT_WRITE,VM_PROT_READ|VM_PROT_WRITE,VM_INHERIT_NONE);
  printf("REMOTE_VM_MAP_RETURN result=%d address=%llx\n",result,remote);assert(!result);
  // The target maps the actual shared backing; this is not a copied result.
  ((unsigned char*)original)[19]=0xa6;
  struct {mach_msg_header_t h;mach_vm_address_t address;} out={0};out.h.msgh_bits=MACH_MSGH_BITS(MACH_MSG_TYPE_COPY_SEND,0);out.h.msgh_remote_port=server;out.h.msgh_id=3;out.address=remote;assert(!mach_msg(&out.h,MACH_SEND_MSG,sizeof(out),0,0,0,0));
  assert(!mach_port_deallocate(mach_task_self(),entry));assert(!mach_vm_deallocate(mach_task_self(),original,4096));_exit(0);
 }
 close(pipefd[0]);
 // Force an event-manager and worker thread in the recipient before remote VM.
 dispatch_semaphore_t sem=dispatch_semaphore_create(0);
 dispatch_async(dispatch_get_global_queue(0,0),^{dispatch_semaphore_signal(sem);});assert(!dispatch_semaphore_wait(sem,dispatch_time(DISPATCH_TIME_NOW,5*NSEC_PER_SEC)));
 dispatch_source_t timer=dispatch_source_create(DISPATCH_SOURCE_TYPE_TIMER,0,0,dispatch_get_global_queue(0,0));dispatch_source_set_timer(timer,dispatch_time(DISPATCH_TIME_NOW,60*NSEC_PER_SEC),60*NSEC_PER_SEC,0);dispatch_source_set_event_handler(timer,^{});dispatch_resume(timer);
 usleep(300000);assert(write(pipefd[1],"x",1)==1);close(pipefd[1]);
 union incoming request;receive(port,&request);struct capability response={0};response.h.msgh_bits=MACH_MSGH_BITS(MACH_MSG_TYPE_MOVE_SEND_ONCE,0)|MACH_MSGH_BITS_COMPLEX;response.h.msgh_remote_port=request.cap.h.msgh_remote_port;response.h.msgh_id=2;response.body.msgh_descriptor_count=1;response.task.name=mach_task_self();response.task.type=MACH_MSG_PORT_DESCRIPTOR;response.task.disposition=MACH_MSG_TYPE_COPY_SEND;assert(!mach_msg(&response.h,MACH_SEND_MSG,sizeof(response),0,0,0,0));
 receive(port,&request);assert(request.cap.h.msgh_id==3);mach_vm_address_t address;memcpy(&address,request.bytes+sizeof(mach_msg_header_t),sizeof(address));assert(((unsigned char*)address)[19]==0xa6);assert(!mach_vm_deallocate(mach_task_self(),address,4096));
 int status;assert(waitpid(child,&status,0)==child&&WIFEXITED(status)&&WEXITSTATUS(status)==0);dispatch_source_cancel(timer);dispatch_release(timer);dispatch_release(sem);assert(!mach_port_destroy(mach_task_self(),port));puts("NATIVE_REMOTE_VM_MAP_MULTITHREADED_RECIPIENT_SHARING_OK");return 0;
}
