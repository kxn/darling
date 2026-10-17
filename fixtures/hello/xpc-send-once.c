#include <xpc/xpc.h>
#include <mach/mach.h>
#include <dlfcn.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef xpc_object_t (*Create)(mach_port_t);
typedef mach_port_t (*Extract)(xpc_object_t);

static mach_port_t make_right(mach_port_t *receiver) {
    mach_port_t right=MACH_PORT_NULL;mach_msg_type_name_t acquired=0;
    assert(mach_port_allocate(mach_task_self(),MACH_PORT_RIGHT_RECEIVE,receiver)==KERN_SUCCESS);
    assert(mach_port_extract_right(mach_task_self(),*receiver,MACH_MSG_TYPE_MAKE_SEND_ONCE,&right,&acquired)==KERN_SUCCESS);
    assert(acquired==MACH_MSG_TYPE_PORT_SEND_ONCE);
    mach_port_type_t type=0;
    assert(mach_port_type(mach_task_self(),right,&type)==KERN_SUCCESS && (type&MACH_PORT_TYPE_SEND_ONCE));
    return right;
}

int main(int argc,char **argv) {
    if (argc<2 || argc>3) return 2;
    void *library=dlopen(argv[1],RTLD_LAZY|RTLD_LOCAL);
    if (!library) { fprintf(stderr,"%s\n",dlerror());return 3; }
    Create create=(Create)dlsym(library,"xpc_mach_send_once_create");
    Extract extract=(Extract)dlsym(library,"xpc_mach_send_once_extract_right");
    xpc_type_t type=(xpc_type_t)dlsym(library,"_xpc_type_mach_send_once");
    assert(create && extract && type);
    if (argc==3) {
        assert(!strcmp(argv[2],"--double-extract"));
        xpc_object_t empty=create(MACH_PORT_NULL);assert(empty);
        assert(extract(empty)==MACH_PORT_NULL);extract(empty);
        return 99;
    }
    xpc_object_t wrong=xpc_int64_create(-7);
    assert(extract(wrong)==MACH_PORT_NULL && xpc_int64_get_value(wrong)==-7);xpc_release(wrong);
    mach_port_t receiver=0,right=make_right(&receiver);
    xpc_object_t object=create(right);assert(object && xpc_get_type(object)==type);
    mach_port_urefs_t refs=0;
    assert(mach_port_get_refs(mach_task_self(),right,MACH_PORT_RIGHT_SEND_ONCE,&refs)==KERN_SUCCESS && refs==1);
    xpc_object_t copy=xpc_copy(object);assert(copy==object);
    assert(mach_port_get_refs(mach_task_self(),right,MACH_PORT_RIGHT_SEND_ONCE,&refs)==KERN_SUCCESS && refs==1);
    xpc_release(copy);
    char *description=xpc_copy_description(object);assert(description && strstr(description,"send_once"));free(description);
    assert(extract(object)==right);xpc_release(object);
    mach_port_type_t rights=0;
    assert(mach_port_type(mach_task_self(),right,&rights)==KERN_SUCCESS && (rights&MACH_PORT_TYPE_SEND_ONCE));
    mach_msg_header_t message={0};message.msgh_bits=MACH_MSGH_BITS(MACH_MSG_TYPE_MOVE_SEND_ONCE,0);
    message.msgh_remote_port=right;message.msgh_size=sizeof(message);message.msgh_id=8732;
    assert(mach_msg(&message,MACH_SEND_MSG|MACH_SEND_TIMEOUT,sizeof(message),0,MACH_PORT_NULL,1000,MACH_PORT_NULL)==MACH_MSG_SUCCESS);
    union { mach_msg_header_t header; unsigned char bytes[512]; } incoming;
    memset(&incoming,0,sizeof(incoming));incoming.header.msgh_local_port=receiver;
    assert(mach_msg(&incoming.header,MACH_RCV_MSG|MACH_RCV_TIMEOUT,0,sizeof(incoming),receiver,1000,MACH_PORT_NULL)==MACH_MSG_SUCCESS);
    assert(incoming.header.msgh_id==8732);mach_msg_destroy(&incoming.header);
    rights=0;
    assert(mach_port_type(mach_task_self(),right,&rights)!=KERN_SUCCESS || !(rights&MACH_PORT_TYPE_SEND_ONCE));
    assert(mach_port_destroy(mach_task_self(),receiver)==KERN_SUCCESS);
    right=make_right(&receiver);object=create(right);assert(object);xpc_release(object);
    rights=0;
    assert(mach_port_type(mach_task_self(),right,&rights)!=KERN_SUCCESS || !(rights&MACH_PORT_TYPE_SEND_ONCE));
    assert(mach_port_destroy(mach_task_self(),receiver)==KERN_SUCCESS);
    puts("XPC_SEND_ONCE_REAL_RIGHT_COPY_EXTRACTION_DELIVERY_CONSUMPTION_DISPOSAL_WRONG_TYPE_OK");
    return 0;
}
