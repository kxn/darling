#include <mach/mach.h>
#include <mach/task_info.h>
#include <servers/bootstrap.h>
#include "../../vendor/darling/src/launchd/liblaunch/bootstrap_priv.h"
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static unsigned checks;
#define CHECK(x) do { checks++; if (!(x)) { fprintf(stderr,"FAIL line=%d expression=%s pid=%d\n",__LINE__,#x,getpid()); exit(1); } } while (0)
struct message { mach_msg_header_t header; uint32_t value; };
static audit_token_t token(void) {
    audit_token_t result; mach_msg_type_number_t count=TASK_AUDIT_TOKEN_COUNT;
    CHECK(task_info(mach_task_self(),TASK_AUDIT_TOKEN,(task_info_t)&result,&count)==KERN_SUCCESS);
    CHECK(count==TASK_AUDIT_TOKEN_COUNT && result.val[5]==(unsigned)getpid() && result.val[7]);
    return result;
}
static void send(mach_port_t port) {
    struct message m={0}; m.header.msgh_bits=MACH_MSGH_BITS(MACH_MSG_TYPE_COPY_SEND,0);
    m.header.msgh_size=sizeof(m); m.header.msgh_remote_port=port; m.header.msgh_id=0x7050; m.value=0xbeef1234;
    CHECK(mach_msg(&m.header,MACH_SEND_MSG|MACH_SEND_TIMEOUT,sizeof(m),0,MACH_PORT_NULL,3000,MACH_PORT_NULL)==MACH_MSG_SUCCESS);
}
static void receive(mach_port_t port) {
    struct { struct message message; mach_msg_max_trailer_t trailer; } m={0};
    CHECK(mach_msg(&m.message.header,MACH_RCV_MSG|MACH_RCV_TIMEOUT,0,sizeof(m),port,3000,MACH_PORT_NULL)==MACH_MSG_SUCCESS);
    CHECK(m.message.header.msgh_id==0x7050 && m.message.value==0xbeef1234);
}
static mach_port_t receiver(void) {
    mach_port_t p=MACH_PORT_NULL;
    CHECK(mach_port_allocate(mach_task_self(),MACH_PORT_RIGHT_RECEIVE,&p)==KERN_SUCCESS);
    CHECK(mach_port_insert_right(mach_task_self(),p,p,MACH_MSG_TYPE_MAKE_SEND)==KERN_SUCCESS);
    return p;
}
int main(int argc,char **argv) {
    setbuf(stdout,NULL); CHECK(argc>=2);
    if (!strcmp(argv[1],"--child")) {
        CHECK(argc==3); audit_token_t t=token(); mach_port_t port=MACH_PORT_NULL;
        CHECK(bootstrap_look_up(bootstrap_port,argv[2],&port)==BOOTSTRAP_SUCCESS);
        send(port); CHECK(mach_port_deallocate(mach_task_self(),port)==KERN_SUCCESS);
        printf("LAUNCHD_SANDBOX_EXEC_CHILD pid=%u version=%u\n",t.val[5],t.val[7]); return 0;
    }
    CHECK(argc==2); int capture=!strcmp(argv[1],"capture"); audit_token_t self=token();
    printf("LAUNCHD_SANDBOX_PARENT pid=%u version=%u capture=%d\n",self.val[5],self.val[7],capture);
    static const char *cases[]={"allow","deny-reg","error-reg","deny-lookup","error-lookup"};
    for (unsigned local=0;local<2;local++) for (unsigned i=0;i<5;i++) {
        char name[128]; snprintf(name,sizeof name,"org.linuxcode.sandbox-test.%s.%u.%d",cases[i],local,getpid());
        mach_port_t port=receiver(); uint64_t flags=local?BOOTSTRAP_PER_PID_SERVICE:0;
        kern_return_t expected=capture&&(i==1||i==2)?BOOTSTRAP_NOT_PRIVILEGED:BOOTSTRAP_SUCCESS;
        kern_return_t actual=bootstrap_register2(bootstrap_port,name,port,flags);
        printf("LAUNCHD_SANDBOX_REGISTER name=%s status=%d expected=%d\n",name,actual,expected); CHECK(actual==expected);
        mach_port_t found=MACH_PORT_NULL;
        actual=bootstrap_look_up2(bootstrap_port,name,&found,local?getpid():0,flags);
        expected=capture&&(i==1||i==2)?BOOTSTRAP_UNKNOWN_SERVICE:capture&&(i==3||i==4)?BOOTSTRAP_NOT_PRIVILEGED:BOOTSTRAP_SUCCESS;
        printf("LAUNCHD_SANDBOX_LOOKUP name=%s status=%d expected=%d\n",name,actual,expected); CHECK(actual==expected);
        if (actual==BOOTSTRAP_SUCCESS) {
            send(found); receive(port); CHECK(mach_port_deallocate(mach_task_self(),found)==KERN_SUCCESS);
        } else CHECK(found==MACH_PORT_NULL);
        CHECK(mach_port_destroy(mach_task_self(),port)==KERN_SUCCESS);
    }
    // Unknown-service check-in returns a receive right, a separate launchd
    // route from bootstrap_register2's transfer of an existing send right.
    for (unsigned local=0;local<2;local++) for (unsigned i=0;i<3;i++) {
        char name[128]; snprintf(name,sizeof name,"org.linuxcode.sandbox-test.%s.checkin.%u.%d",cases[i],local,getpid());
        uint64_t flags=local?BOOTSTRAP_PER_PID_SERVICE:0;
        mach_port_t incoming=MACH_PORT_NULL, found=MACH_PORT_NULL;
        kern_return_t expected=capture&&i?BOOTSTRAP_NOT_PRIVILEGED:BOOTSTRAP_SUCCESS;
        kern_return_t actual=bootstrap_check_in2(bootstrap_port,name,&incoming,flags);
        printf("LAUNCHD_SANDBOX_CHECKIN name=%s status=%d expected=%d\n",name,actual,expected); CHECK(actual==expected);
        actual=bootstrap_look_up2(bootstrap_port,name,&found,local?getpid():0,flags);
        CHECK(actual==(capture&&i?BOOTSTRAP_UNKNOWN_SERVICE:BOOTSTRAP_SUCCESS));
        if (actual==BOOTSTRAP_SUCCESS) {
            send(found); receive(incoming); CHECK(mach_port_deallocate(mach_task_self(),found)==KERN_SUCCESS);
            CHECK(mach_port_destroy(mach_task_self(),incoming)==KERN_SUCCESS);
        } else CHECK(incoming==MACH_PORT_NULL && found==MACH_PORT_NULL);
    }
    char name[128]; snprintf(name,sizeof name,"org.linuxcode.sandbox-test.exec.%d",getpid());
    mach_port_t port=receiver(); CHECK(bootstrap_register(bootstrap_port,name,port)==BOOTSTRAP_SUCCESS);
    pid_t child=fork(); CHECK(child>=0);
    if (!child) { execl(argv[0],argv[0],"--child",name,(char *)NULL); _exit(99); }
    receive(port); int status=0; CHECK(waitpid(child,&status,0)==child && WIFEXITED(status) && WEXITSTATUS(status)==0);
    CHECK(mach_port_destroy(mach_task_self(),port)==KERN_SUCCESS);
    printf("LAUNCHD_SANDBOX_REGISTRATION_LOOKUP_MESSAGE_AND_EXEC_OK checks=%u capture=%d\n",checks,capture);
    return 0;
}
