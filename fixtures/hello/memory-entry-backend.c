#include <assert.h>
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <mach/memory_object_types.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
    assert(argc == 2);
    setbuf(stdout, NULL);
    vm_prot_t permission = (vm_prot_t)strtoul(argv[1], NULL, 0);
    mach_vm_address_t original = 0;
    assert(mach_vm_allocate(mach_task_self(), &original, 4096, VM_FLAGS_ANYWHERE) == KERN_SUCCESS);
    memset((void *)original, 0x73, 4096);
    memory_object_size_t size = 4096;
    mach_port_t entry = MACH_PORT_NULL;
    printf("MEMORY_ENTRY_REAL_BACKEND_BEGIN FLAGS=%#x ORIGINAL=%#llx\n", permission, original);
    kern_return_t result = mach_make_memory_entry_64(mach_task_self(), &size,
            original, permission, &entry, MACH_PORT_NULL);
    printf("MEMORY_ENTRY_REAL_BACKEND_CREATE RESULT=%d ENTRY=%u SIZE=%llu\n", result, entry, size);
    if (result != KERN_SUCCESS || !MACH_PORT_VALID(entry)) return 3;
    mach_vm_address_t mapped = 0;
    result = mach_vm_map(mach_task_self(), &mapped, size, 0, VM_FLAGS_ANYWHERE,
            entry, 0, FALSE, VM_PROT_READ | VM_PROT_WRITE,
            VM_PROT_READ | VM_PROT_WRITE, VM_INHERIT_NONE);
    printf("MEMORY_ENTRY_REAL_BACKEND_MAP RESULT=%d ADDRESS=%#llx\n", result, mapped);
    if (result != KERN_SUCCESS || !mapped || mapped == original) return 4;
    assert(*(volatile unsigned char *)mapped == 0x73);
    *(volatile unsigned char *)mapped = 0x42;
    assert(*(volatile unsigned char *)original == 0x42);
    *(volatile unsigned char *)original = 0x19;
    assert(*(volatile unsigned char *)mapped == 0x19);
    assert(mach_vm_deallocate(mach_task_self(), mapped, size) == KERN_SUCCESS);
    assert(mach_port_deallocate(mach_task_self(), entry) == KERN_SUCCESS);
    assert(mach_vm_deallocate(mach_task_self(), original, 4096) == KERN_SUCCESS);
    puts("MEMORY_ENTRY_REAL_BACKEND_SHARED_ALIAS_AND_OWNERSHIP_OK");
    return 0;
}
