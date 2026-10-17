#include <TargetConditionals.h>
#include <mach/machine.h>
#include <mach-o/dyld.h>
#include "../../vendor/apple-dyld/include/mach-o/utils.h"
#include <assert.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

struct Case { const char *name;cpu_type_t type;cpu_subtype_t subtype; };
static const struct Case cases[]={
 {"x86_64",CPU_TYPE_X86_64,CPU_SUBTYPE_X86_64_ALL},{"x86_64h",CPU_TYPE_X86_64,CPU_SUBTYPE_X86_64_H},
 {"i386",CPU_TYPE_I386,CPU_SUBTYPE_I386_ALL},{"ppc",CPU_TYPE_POWERPC,CPU_SUBTYPE_POWERPC_ALL},
 {"arm64",CPU_TYPE_ARM64,CPU_SUBTYPE_ARM64_ALL},{"arm64e",CPU_TYPE_ARM64,CPU_SUBTYPE_ARM64E|0x80000000},
 {"arm64e.kernel",CPU_TYPE_ARM64,CPU_SUBTYPE_ARM64E|0xc0000000},
 {"arm64e.kernel.v1",CPU_TYPE_ARM64,CPU_SUBTYPE_ARM64E|0xc1000000},
 {"arm64e.kernel.v2",CPU_TYPE_ARM64,CPU_SUBTYPE_ARM64E|0xc2000000},
 {"arm64_32",CPU_TYPE_ARM64_32,CPU_SUBTYPE_ARM64_32_V8},
 {"armv4t",CPU_TYPE_ARM,CPU_SUBTYPE_ARM_V4T},{"armv6",CPU_TYPE_ARM,CPU_SUBTYPE_ARM_V6},
 {"armv6m",CPU_TYPE_ARM,CPU_SUBTYPE_ARM_V6M},{"thumbv6m",CPU_TYPE_ARM,CPU_SUBTYPE_ARM_V6M},
 {"armv7k",CPU_TYPE_ARM,CPU_SUBTYPE_ARM_V7K},{"thumbv7k",CPU_TYPE_ARM,CPU_SUBTYPE_ARM_V7K},
 {"armv7m",CPU_TYPE_ARM,CPU_SUBTYPE_ARM_V7M},{"thumbv7m",CPU_TYPE_ARM,CPU_SUBTYPE_ARM_V7M},
 {"armv7em",CPU_TYPE_ARM,CPU_SUBTYPE_ARM_V7EM},{"thumbv7em",CPU_TYPE_ARM,CPU_SUBTYPE_ARM_V7EM},
 {"armv8m.main",CPU_TYPE_ARM,17},{"thumbv8m.main",CPU_TYPE_ARM,17},
 {"armv8.1m.main",CPU_TYPE_ARM,19},{"thumbv8.1m.main",CPU_TYPE_ARM,19},
 {"armv7s",CPU_TYPE_ARM,CPU_SUBTYPE_ARM_V7S},{"thumbv7s",CPU_TYPE_ARM,CPU_SUBTYPE_ARM_V7S},
 {"armv7",CPU_TYPE_ARM,CPU_SUBTYPE_ARM_V7},{"thumbv7",CPU_TYPE_ARM,CPU_SUBTYPE_ARM_V7}
};
int main(void) {
    void *system=dlopen("/usr/lib/libSystem.B.dylib",RTLD_LAZY|RTLD_LOCAL);assert(system);
    assert(dlsym(system,"macho_cpu_type_for_arch_name")==macho_cpu_type_for_arch_name);
    for(unsigned i=0;i<sizeof(cases)/sizeof(cases[0]);i++) {
        cpu_type_t type=123;cpu_subtype_t subtype=456;
        assert(macho_cpu_type_for_arch_name(cases[i].name,&type,&subtype));
        assert(type==cases[i].type && subtype==cases[i].subtype);
        const char *canonical=macho_arch_name_for_cpu_type(type,subtype);assert(canonical);
        if(!strncmp(cases[i].name,"arm64e",6))assert(!strcmp(canonical,"arm64e"));
        else assert(!strncmp(cases[i].name,"thumb",5) || !strcmp(canonical,cases[i].name));
    }
    const char *unknown[]={"no-such-architecture","ARM64","ppc64","arm64e.old",""};
    for(unsigned i=0;i<sizeof(unknown)/sizeof(unknown[0]);i++) {
        cpu_type_t type=123;cpu_subtype_t subtype=456;
        assert(!macho_cpu_type_for_arch_name(unknown[i],&type,&subtype));assert(type==123 && subtype==456);
    }
    assert(!macho_arch_name_for_cpu_type(123,456));
    assert(!strcmp(macho_arch_name_for_cpu_type(CPU_TYPE_X86_64,CPU_SUBTYPE_X86_64_H|CPU_SUBTYPE_LIB64),"x86_64h"));
    const struct mach_header *header=_dyld_get_image_header(0);assert(header);
    assert(!strcmp(macho_arch_name_for_mach_header(NULL),macho_arch_name_for_cpu_type(header->cputype,header->cpusubtype)));
    printf("ORIGINAL_DYLD_ARCHITECTURE_METADATA_NAMES_ALIASES_FLAGS_UNKNOWN_MAIN_HEADER_OK %zu\n",sizeof(cases)/sizeof(cases[0]));
    return 0;
}
