#include <xpc/xpc.h>
#include <dispatch/dispatch.h>
#include <assert.h>
#include <stdio.h>
#include <stdatomic.h>
static void wait_one(dispatch_semaphore_t semaphore) {
    assert(!dispatch_semaphore_wait(semaphore,dispatch_time(DISPATCH_TIME_NOW,5*NSEC_PER_SEC)));
}
int main(void) {
    setbuf(stdout,NULL);puts("XPC_REAL_LOOPBACK_CHECKIN_BEGIN");
    for(unsigned cycle=0;cycle<16;cycle++) {
        dispatch_queue_t queue=dispatch_queue_create("test.loopback.listener",NULL);
        dispatch_semaphore_t ready=dispatch_semaphore_create(0),done=dispatch_semaphore_create(0),cancelled=dispatch_semaphore_create(0);
        __block xpc_connection_t accepted=NULL;
        xpc_connection_t listener=xpc_connection_create(NULL,queue);assert(listener);
        xpc_connection_set_event_handler(listener,^(xpc_object_t connection){
            printf("LOOPBACK_LISTENER_EVENT cycle=%u connection=%d\n",cycle,xpc_get_type(connection)==XPC_TYPE_CONNECTION);
            if(xpc_get_type(connection)!=XPC_TYPE_CONNECTION) return;
            accepted=connection;xpc_retain(accepted);
            xpc_connection_set_event_handler(connection,^(xpc_object_t message){
                if(xpc_get_type(message)!=XPC_TYPE_DICTIONARY)return;
                xpc_object_t reply=xpc_dictionary_create_reply(message);assert(reply);
                xpc_dictionary_set_uint64(reply,"response",xpc_dictionary_get_uint64(message,"request")^0x12345678);
                xpc_connection_send_message(connection,reply);xpc_release(reply);
            });
            xpc_connection_resume(connection);dispatch_semaphore_signal(ready);
        });
        xpc_connection_resume(listener);
        xpc_endpoint_t endpoint=xpc_endpoint_create(listener);assert(endpoint);
        xpc_connection_t client=xpc_connection_create_from_endpoint(endpoint);assert(client);xpc_release(endpoint);
        xpc_connection_set_event_handler(client,^(xpc_object_t event){
            if(event==XPC_ERROR_CONNECTION_INVALID)dispatch_semaphore_signal(cancelled);
        });
        xpc_connection_resume(client);
        for(unsigned i=0;i<16;i++) {
            uint64_t value=cycle*16+i;
            xpc_object_t message=xpc_dictionary_create(NULL,NULL,0);assert(message);
            xpc_dictionary_set_uint64(message,"request",value);
            xpc_connection_send_message_with_reply(client,message,dispatch_get_global_queue(0,0),^(xpc_object_t reply){
                assert(xpc_get_type(reply)==XPC_TYPE_DICTIONARY);
                assert(xpc_dictionary_get_uint64(reply,"response")== (value^0x12345678));
                dispatch_semaphore_signal(done);
            });
            xpc_release(message);
            if(i==0) { wait_one(ready);printf("LOOPBACK_CHECKIN_READY cycle=%u\n",cycle); }
            wait_one(done);
        }
        xpc_connection_cancel(client);wait_one(cancelled);
        xpc_connection_cancel(accepted);xpc_release(accepted);xpc_connection_cancel(listener);
        xpc_release(client);xpc_release(listener);
        dispatch_release(ready);dispatch_release(done);dispatch_release(cancelled);dispatch_release(queue);
    }
    puts("XPC_REAL_16_LOOPBACK_CHECKINS_256_REPLY_PAYLOADS_AND_CANCELLATION_OK");
    return 0;
}
