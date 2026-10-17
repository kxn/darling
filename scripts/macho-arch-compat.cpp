// Public adapters use the unmodified pinned dyld Architecture implementation.
#include "Architecture.h"
#include <mach-o/dyld.h>
#include <string.h>
#include <string_view>

extern "C" __attribute__((visibility("default")))
bool macho_cpu_type_for_arch_name(const char *name,cpu_type_t *type,cpu_subtype_t *subtype) {
    mach_o::Architecture arch=mach_o::Architecture::byName(name);
    if(arch==mach_o::Architecture::invalid)return false;
    *type=arch.cpuType();*subtype=arch.cpuSubtype();return true;
}
extern "C" __attribute__((visibility("default")))
const char *macho_arch_name_for_cpu_type(cpu_type_t type,cpu_subtype_t subtype) {
    const char *name=mach_o::Architecture(type,subtype).name();
    if(!strcmp(name,"unknown"))return nullptr;
    return std::string_view(name).starts_with("arm64e")?"arm64e":name;
}
extern "C" __attribute__((visibility("default")))
const char *macho_arch_name_for_mach_header(const struct mach_header *header) {
    if(!header)header=_dyld_get_image_header(0);
    return macho_arch_name_for_cpu_type(header->cputype,header->cpusubtype);
}
