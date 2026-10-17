#include <sys/resource.h>
#include <sys/syscall.h>
#include <pthread.h>
#include <stdint.h>
#include <stdatomic.h>
#include <unistd.h>
#include <errno.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
static atomic_uint checks,ready,go;
#define check(value) do{atomic_fetch_add(&checks,1);if(!(value)){fprintf(stderr,"MATERIALIZE_POLICY_FAIL line=%d errno=%d\n",__LINE__,errno);exit(1);}}while(0)
static void* worker(void* value) {
 unsigned index=(unsigned)(uintptr_t)value;
 check(getiopolicy_np(IOPOL_TYPE_VFS_MATERIALIZE_DATALESS_FILES,IOPOL_SCOPE_THREAD)==IOPOL_MATERIALIZE_DATALESS_FILES_DEFAULT);
 atomic_fetch_add(&ready,1);while(!atomic_load(&go))sched_yield();
 for(unsigned i=0;i<64;i++){int policy=(i+index)%3;check(!setiopolicy_np(IOPOL_TYPE_VFS_MATERIALIZE_DATALESS_FILES,IOPOL_SCOPE_THREAD,policy));sched_yield();check(getiopolicy_np(IOPOL_TYPE_VFS_MATERIALIZE_DATALESS_FILES,IOPOL_SCOPE_THREAD)==policy);}
 return NULL;
}
int main(void) {
 setbuf(stdout,NULL);const int type=IOPOL_TYPE_VFS_MATERIALIZE_DATALESS_FILES,scope=IOPOL_SCOPE_THREAD;
 check(getiopolicy_np(type,scope)==0);check(!setiopolicy_np(type,scope,1));check(getiopolicy_np(type,scope)==1);
 check(!setiopolicy_np(type,scope,2));check(getiopolicy_np(type,scope)==2);check(!setiopolicy_np(type,scope,1));
 pthread_t threads[8];for(unsigned i=0;i<8;i++)check(!pthread_create(&threads[i],NULL,worker,(void*)(uintptr_t)i));
 while(atomic_load(&ready)!=8)sched_yield();check(getiopolicy_np(type,scope)==1);atomic_store(&go,1);
 for(unsigned i=0;i<8;i++)check(!pthread_join(threads[i],NULL));check(getiopolicy_np(type,scope)==1);
 errno=0;check(setiopolicy_np(type,scope,3)==-1 && errno==EINVAL);check(getiopolicy_np(type,scope)==1);
 errno=0;check(getiopolicy_np(type,IOPOL_SCOPE_DARWIN_BG)==-1 && errno==EINVAL);
 errno=0;check(getiopolicy_np(type,IOPOL_SCOPE_PROCESS)==-1 && errno==ENOTSUP);
 errno=0;check(getiopolicy_np(IOPOL_TYPE_DISK,scope)==-1 && errno==ENOTSUP);
 struct {int scope,type,policy;} param={1,3,12345};errno=0;check(syscall(SYS_iopolicysys,0,&param)==-1 && errno==EINVAL);check(param.policy==12345);
 errno=0;check(syscall(SYS_iopolicysys,1,NULL)==-1 && errno==EFAULT);
 check(!setiopolicy_np(type,scope,0));check(getiopolicy_np(type,scope)==0);
 printf("NATIVE_MATERIALIZE_THREAD_POLICY_ROUNDTRIP_ISOLATION_8_THREADS_512_UPDATES_ERRORS_OK checks=%u\n",atomic_load(&checks));return 0;
}
