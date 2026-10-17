#include <TargetConditionals.h>
#include <uuid/uuid.h>
#include <mach-o/dyld.h>
#include "../../vendor/apple-dyld/include/mach-o/dyld_introspection.h"
#include <mach/mach.h>
#include <assert.h>
#include <dlfcn.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static const char *fixture_name="/usr/lib/libLinuxcodeSnapshotFixture.dylib";
static uint8_t main_uuid[16];static const struct mach_header_64 *main_header;
static uint64_t main_text_address,main_text_size;
static unsigned inspect(dyld_process_snapshot_t snapshot,unsigned expected_fixture,const char *main_path) {
    assert(!dyld_process_snapshot_get_shared_cache(snapshot));
    __block unsigned count=0,main_count=0,fixtures=0;
    dyld_process_snapshot_for_each_image(snapshot,^(dyld_image_t image) {
        count++;const char *name=dyld_image_get_installname(image);
        if(name && !strcmp(name,fixture_name))fixtures++;
        const char *path=dyld_image_get_file_path(image);
        if(!path || strcmp(path,main_path))return;
        main_count++;uuid_t uuid;assert(dyld_image_copy_uuid(image,&uuid));assert(!memcmp(uuid,main_uuid,16));
        __block bool found=false;
        assert(dyld_image_for_each_segment_info(image,^(const char *segment,uint64_t address,uint64_t size,int permission) {
            assert(strcmp(segment,"__PAGEZERO"));
            if(!strcmp(segment,"__TEXT")) {
                assert(address==main_text_address && size==main_text_size && (permission&VM_PROT_EXECUTE));found=true;
            }
        }));
        assert(found);
        __block bool content=false;
        assert(dyld_image_content_for_segment(image,"__TEXT",^(const void *bytes,uint64_t address,uint64_t size) {
            assert(address==main_text_address && size==main_text_size);
            assert(!memcmp(bytes,main_header,64));content=true;
        }));assert(content);
    });
    assert(count>10 && main_count==1 && fixtures==expected_fixture);return count;
}
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    main_header=(const void *)_dyld_get_image_header(0);assert(main_header && main_header->magic==MH_MAGIC_64);
    const struct load_command *command=(const void *)(main_header+1);bool have_uuid=false;
    for(unsigned i=0;i<main_header->ncmds;i++) {
        if(command->cmd==LC_UUID){memcpy(main_uuid,((const struct uuid_command *)command)->uuid,16);have_uuid=true;}
        if(command->cmd==LC_SEGMENT_64) {
            const struct segment_command_64 *segment=(const void *)command;
            if(!strncmp(segment->segname,"__TEXT",16)) {
                main_text_address=segment->vmaddr+_dyld_get_image_vmaddr_slide(0);main_text_size=segment->vmsize;
            }
        }
        command=(const void *)((const char *)command+command->cmdsize);
    }
    assert(have_uuid && main_text_size);
    const char *main_path=_dyld_get_image_name(0);assert(main_path);
    mach_port_urefs_t initial_refs=0,final_refs=0;
    assert(mach_port_get_refs(mach_task_self(),mach_task_self(),MACH_PORT_RIGHT_SEND,&initial_refs)==KERN_SUCCESS);
    kern_return_t result=KERN_SUCCESS;
    assert(!dyld_process_create_for_task(MACH_PORT_NULL,&result) && result!=KERN_SUCCESS);
    dyld_process_t process=dyld_process_create_for_task(mach_task_self(),&result);assert(process && result==KERN_SUCCESS);
    dyld_process_snapshot_t before=dyld_process_snapshot_create_for_process(process,&result);assert(before && result==KERN_SUCCESS);
    unsigned baseline=inspect(before,0,main_path);
    void *library=dlopen(argv[1],RTLD_LAZY|RTLD_LOCAL);if(!library){fprintf(stderr,"%s\n",dlerror());return 1;}
    int (*marker)(void)=(int(*)(void))dlsym(library,"linuxcode_snapshot_marker");assert(marker && marker()==731);
    dyld_process_snapshot_t loaded=dyld_process_snapshot_create_for_process(process,&result);assert(loaded && result==KERN_SUCCESS);
    assert(inspect(loaded,1,main_path)==baseline+1);
    assert(inspect(before,0,main_path)==baseline);
    assert(!dlclose(library));
    dyld_process_snapshot_t after=dyld_process_snapshot_create_for_process(process,&result);assert(after && result==KERN_SUCCESS);
    assert(inspect(after,0,main_path)==baseline);
    dyld_process_dispose(process);
    assert(inspect(loaded,1,main_path)==baseline+1); /* Snapshot keeps its own state/task right. */
    dyld_process_snapshot_dispose(before);dyld_process_snapshot_dispose(loaded);dyld_process_snapshot_dispose(after);
    process=dyld_process_create_for_current_task();assert(process);dyld_process_dispose(process);
    assert(mach_port_get_refs(mach_task_self(),mach_task_self(),MACH_PORT_RIGHT_SEND,&final_refs)==KERN_SUCCESS);
    assert(initial_refs==final_refs);
    printf("REAL_DYLD_PROCESS_SNAPSHOT_MACH_IMAGES_UUID_SEGMENTS_CONTENT_LOAD_UNLOAD_FROZEN_STATE_RIGHTS_OK %u\n",baseline);
    return 0;
}
