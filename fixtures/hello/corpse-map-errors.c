#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
static unsigned checks;
#define CHECK(x) do { __atomic_fetch_add(&checks,1,__ATOMIC_RELAXED);if(!(x)){fprintf(stderr,"CORPSE_MAP_FAIL line=%d %s\n",__LINE__,#x);abort();} } while(0)
static void* work(void* unused) {
    for(unsigned i=0;i<32;i++) {
        mach_vm_address_t address=UINT64_C(0x123456789);mach_vm_size_t size=UINT64_C(0x987654321);
        CHECK(task_map_corpse_info_64(mach_task_self(),mach_task_self(),&address,&size)==KERN_INVALID_ARGUMENT);
        // MIG does not copy successful out arguments on an error reply.
        CHECK(address==UINT64_C(0x123456789)&&size==UINT64_C(0x987654321));
        vm_address_t oldAddress=0x12345678;uint32_t oldSize=0x76543210;
        CHECK(task_map_corpse_info(mach_task_self(),mach_task_self(),&oldAddress,&oldSize)==KERN_INVALID_ARGUMENT);
        CHECK(oldAddress==0x12345678&&oldSize==0x76543210);
        mach_vm_address_t page=0;CHECK(mach_vm_allocate(mach_task_self(),&page,4096,VM_FLAGS_ANYWHERE)==KERN_SUCCESS);
        volatile uint64_t* data=(void*)(uintptr_t)page;*data=UINT64_C(0xf123456789abcdef);CHECK(*data==UINT64_C(0xf123456789abcdef));
        CHECK(mach_vm_deallocate(mach_task_self(),page,4096)==KERN_SUCCESS);
    }
    return NULL;
}
int main(void) {
    setbuf(stdout,NULL);pthread_t threads[8];
    for(unsigned i=0;i<8;i++)CHECK(!pthread_create(&threads[i],NULL,work,NULL));
    for(unsigned i=0;i<8;i++)CHECK(!pthread_join(threads[i],NULL));
    printf("CORPSE_MAP_LIVE_TASK_ERRORS_AND_SERVER_SURVIVAL_OK checks=%u rpc_errors=512 real_vm_cycles=256 threads=8\n",checks);
    return 0;
}
