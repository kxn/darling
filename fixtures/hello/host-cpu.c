#include <mach/mach.h>
#include <mach/host_info.h>
#include <mach/processor_info.h>
#include <dlfcn.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>

int main(int argc,char **argv) {
    if (argc!=3) return 2;
    int after=!strcmp(argv[1],"--after"),before=!strcmp(argv[1],"--before");
    if (!after && !before) return 2;
    int expected=after ? CPU_SUBTYPE_X86_64_H : CPU_SUBTYPE_X86_64_ALL;
    mach_port_t host=mach_host_self();host_basic_info_data_t basic={0};
    mach_msg_type_number_t count=HOST_BASIC_INFO_COUNT;
    assert(host_info(host,HOST_BASIC_INFO,(host_info_t)&basic,&count)==KERN_SUCCESS);
    assert(basic.cpu_subtype==expected);
    host_preferred_user_arch_data_t preferred={0};count=HOST_PREFERRED_USER_ARCH_COUNT;
    assert(host_info(host,HOST_PREFERRED_USER_ARCH,(host_info_t)&preferred,&count)==KERN_SUCCESS);
    assert(preferred.cpu_subtype==expected);
    natural_t cpus=0;processor_info_array_t array=NULL;mach_msg_type_number_t entries=0;
    kern_return_t processor_status=host_processor_info(host,PROCESSOR_BASIC_INFO,&cpus,&array,&entries);
    int processor_subtype=-1;
    if (processor_status==KERN_SUCCESS) {
        assert(cpus && entries>=PROCESSOR_BASIC_INFO_COUNT);
        processor_basic_info_t info=(processor_basic_info_t)array;processor_subtype=info->cpu_subtype;
        assert(processor_subtype==expected);
        vm_deallocate(mach_task_self(),(vm_address_t)array,entries*sizeof(integer_t));
    }
    printf("HOST_CPU type=%d subtype=%d preferred_type=%d preferred_subtype=%d processor_status=%d processor_subtype=%d\n",
        basic.cpu_type,basic.cpu_subtype,preferred.cpu_type,preferred.cpu_subtype,processor_status,processor_subtype);
    mach_port_deallocate(mach_task_self(),host);
    void *library=dlopen(argv[2],RTLD_LAZY|RTLD_LOCAL);
    if (before) {
        assert(!library);
        fprintf(stderr,"EXPECTED_X86_64H_REJECTION: %s\n",dlerror());
        puts("LEGACY_CPU_REPORT_X86_64H_LIBRARY_REJECTION_CONFIRMED");return 0;
    }
    if (!library) { fprintf(stderr,"%s\n",dlerror());return 3; }
    void (*add)(const int *,int *)=(void (*)(const int *,int *))dlsym(library,"haswell_add_seven");assert(add);
    int input[8]={1,2,3,4,-5,-6,-7,-8},output[8]={0};add(input,output);
    for (unsigned i=0;i<8;++i) assert(output[i]==input[i]+7);
    puts("HOST_CPU_X86_64H_REPORT_AND_ORIGINAL_APPLE_AVX2_LIBRARY_EXECUTION_OK");
    return 0;
}
