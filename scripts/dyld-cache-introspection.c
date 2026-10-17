/* Read-only x86_64 cache introspection following the pinned dyld SPI/format.
 * Handles and content live only within synchronous callbacks. No code execution,
 * cache loading or contiguous pinned mappings are provided. Process snapshots
 * delegate to the existing Darling process-info and Mach-memory implementation.
 */
#include <TargetConditionals.h>
#include <uuid/uuid.h>
#include <mach-o/dyld_introspection.h>
#include <mach-o/dyld_cache_format.h>
#include <assert.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include "legacy-dyld-process-abi.h"
#include <xpc/xpc.h>

/* The existing libxpc implements the actual allocation/mutable dictionary. */
xpc_object_t xpc_dictionary_create_empty(void) { return xpc_dictionary_create(NULL,NULL,0); }

#define CACHE_MAGIC UINT64_C(0x4c58434453434331)
#define IMAGE_MAGIC UINT64_C(0x4c58434453434931)
#define MAX_FILES 65
typedef struct {
    unsigned char *bytes;size_t length;char path[PATH_MAX];
    const struct dyld_cache_mapping_info *maps;uint32_t map_count;
} CacheFile;
struct dyld_shared_cache_s {
    uint64_t magic,base,size;CacheFile files[MAX_FILES];unsigned count;
    const struct dyld_cache_header *header;
};
struct dyld_image_s {
    uint64_t magic,address;struct dyld_shared_cache_s *cache;
    const struct mach_header_64 *header;
    void *owned_header,*file_mapping;size_t file_mapping_size,file_length;
    const unsigned char *file_slice;const char *file_path;
    uint64_t slide;uint8_t uuid[16];bool process_image,has_uuid;
};
#define PROCESS_MAGIC UINT64_C(0x4c58434459505231)
#define SNAPSHOT_MAGIC UINT64_C(0x4c58434459505331)
struct dyld_process_s {uint64_t magic;task_t task;};
struct dyld_process_snapshot_s {uint64_t magic;task_t task;dyld_process_info info;};
static bool range(size_t offset,size_t length,size_t available) {
    return offset<=available && length<=available-offset;
}
static bool header_has(const struct dyld_cache_header *h,size_t offset,size_t length) {
    return range(offset,length,h->mappingOffset);
}
static bool map_file(CacheFile *file,const char *path,const uint8_t *uuid) {
    int descriptor=open(path,O_RDONLY);if(descriptor<0)return false;
    struct stat status;
    if(fstat(descriptor,&status) || !S_ISREG(status.st_mode) || status.st_size<4096 ||
       (uint64_t)status.st_size>UINT64_C(64)*1024*1024*1024) {
        close(descriptor);errno=EINVAL;return false;
    }
    size_t length=(size_t)status.st_size;
    unsigned char *bytes=mmap(NULL,length,PROT_READ,MAP_PRIVATE,descriptor,0);close(descriptor);
    if(bytes==MAP_FAILED)return false;
    const struct dyld_cache_header *h=(const void *)bytes;
    if((memcmp(h->magic,"dyld_v1 x86_64h",15) && memcmp(h->magic,"dyld_v1  x86_64",15)) ||
       !h->mappingCount || h->mappingCount>64 || h->mappingOffset<0x1cc ||
       !range(h->mappingOffset,(size_t)h->mappingCount*sizeof(struct dyld_cache_mapping_info),length) ||
       (uuid && memcmp(uuid,h->uuid,16))) {
        munmap(bytes,length);errno=EINVAL;return false;
    }
    const struct dyld_cache_mapping_info *maps=(const void *)(bytes+h->mappingOffset);
    for(unsigned i=0;i<h->mappingCount;i++) {
        if(!maps[i].size || maps[i].address>UINT64_MAX-maps[i].size ||
           !range(maps[i].fileOffset,maps[i].size,length)) {
            munmap(bytes,length);errno=EINVAL;return false;
        }
    }
    if(strlcpy(file->path,path,sizeof(file->path))>=sizeof(file->path)) {
        munmap(bytes,length);errno=ENAMETOOLONG;return false;
    }
    file->bytes=bytes;file->length=length;file->maps=maps;file->map_count=h->mappingCount;return true;
}
static void close_cache(struct dyld_shared_cache_s *cache) {
    for(unsigned i=0;i<cache->count;i++)munmap(cache->files[i].bytes,cache->files[i].length);
    cache->magic=0;free(cache);
}
static const void *vm_bytes(struct dyld_shared_cache_s *cache,uint64_t address,uint64_t size) {
    for(unsigned i=0;i<cache->count;i++) {
        CacheFile *file=&cache->files[i];
        for(unsigned j=0;j<file->map_count;j++) {
            const struct dyld_cache_mapping_info *m=file->maps+j;
            if(address>=m->address && address-m->address<=m->size && size<=m->size-(address-m->address))
                return file->bytes+m->fileOffset+(address-m->address);
        }
    }
    return NULL;
}
static struct dyld_shared_cache_s *open_cache(const char *path) {
    struct dyld_shared_cache_s *cache=calloc(1,sizeof(*cache));if(!cache)return NULL;
    if(!map_file(cache->files,path,NULL)){free(cache);return NULL;}
    cache->count=1;cache->header=(const void *)cache->files[0].bytes;
    const struct dyld_cache_header *h=cache->header;
    if(!header_has(h,offsetof(struct dyld_cache_header,cacheSubType),4) ||
       h->subCacheArrayCount>=MAX_FILES || !h->sharedRegionSize ||
       h->sharedRegionStart>UINT64_MAX-h->sharedRegionSize ||
       h->imagesTextCount>1000000 ||
       !range(h->imagesTextOffset,h->imagesTextCount*sizeof(struct dyld_cache_image_text_info),cache->files[0].length) ||
       !range(h->subCacheArrayOffset,(size_t)h->subCacheArrayCount*sizeof(struct dyld_subcache_entry),cache->files[0].length)) {
        close_cache(cache);errno=EINVAL;return NULL;
    }
    cache->base=h->sharedRegionStart;cache->size=h->sharedRegionSize;
    const struct dyld_subcache_entry *sub=(const void *)(cache->files[0].bytes+h->subCacheArrayOffset);
    for(unsigned i=0;i<h->subCacheArrayCount;i++) {
        if(!memchr(sub[i].fileSuffix,0,sizeof(sub[i].fileSuffix)) || sub[i].fileSuffix[0]!='.' ||
           strchr(sub[i].fileSuffix,'/')) { close_cache(cache);errno=EINVAL;return NULL; }
        char child[PATH_MAX];
        if(snprintf(child,sizeof(child),"%s%s",path,sub[i].fileSuffix)>=(int)sizeof(child) ||
           !map_file(cache->files+cache->count,child,sub[i].uuid)) {close_cache(cache);return NULL;}
        cache->count++;
        if(cache->files[cache->count-1].maps[0].address<cache->base ||
           cache->files[cache->count-1].maps[0].address-cache->base!=sub[i].cacheVMOffset) {
            close_cache(cache);errno=EINVAL;return NULL;
        }
    }
    for(unsigned i=0;i<cache->count;i++)for(unsigned j=0;j<cache->files[i].map_count;j++) {
        const struct dyld_cache_mapping_info *m=cache->files[i].maps+j;
        if(m->address<cache->base || m->address-cache->base>cache->size ||
           m->size>cache->size-(m->address-cache->base)) {close_cache(cache);errno=EINVAL;return NULL;}
        for(unsigned a=0;a<=i;a++)for(unsigned b=0;b<cache->files[a].map_count;b++) {
            if(a==i && b>=j)break;
            const struct dyld_cache_mapping_info *other=cache->files[a].maps+b;
            if(m->address<other->address+other->size && other->address<m->address+m->size) {
                close_cache(cache);errno=EINVAL;return NULL;
            }
        }
    }
    cache->magic=CACHE_MAGIC;return cache;
}
bool dyld_shared_cache_for_file(const char *path,void (^block)(dyld_shared_cache_t)) {
    if(!path || !block){errno=EINVAL;return false;}
    struct dyld_shared_cache_s *cache=open_cache(path);if(!cache)return false;
    block(cache);close_cache(cache);return true;
}
uint64_t dyld_shared_cache_get_base_address(dyld_shared_cache_t c){assert(c && c->magic==CACHE_MAGIC);return c->base;}
uint64_t dyld_shared_cache_get_mapped_size(dyld_shared_cache_t c){assert(c && c->magic==CACHE_MAGIC);return c->size;}
bool dyld_shared_cache_is_mapped_private(dyld_shared_cache_t c){assert(c && c->magic==CACHE_MAGIC);return true;}
void dyld_shared_cache_copy_uuid(dyld_shared_cache_t c,uuid_t *uuid){assert(c && c->magic==CACHE_MAGIC && uuid);memcpy(uuid,c->header->uuid,16);}
void dyld_shared_cache_for_each_file(dyld_shared_cache_t c,void (^block)(const char *)) {
    assert(c && c->magic==CACHE_MAGIC && block);
    for(unsigned i=0;i<c->count;i++)block(c->files[i].path);
    const uint8_t zero[16]={0};
    if(c->count>1 && memcmp(c->header->symbolFileUUID,zero,16)) {
        char symbols[PATH_MAX];strlcpy(symbols,c->files[0].path,sizeof(symbols));
        char *development=strstr(symbols,".development");if(development)*development=0;
        if(strlcat(symbols,".symbols",sizeof(symbols))<sizeof(symbols))block(symbols);
    }
}
static bool valid_header(const struct mach_header_64 *h,size_t available) {
    if(!h || available<sizeof(*h) || h->magic!=MH_MAGIC_64 || h->cputype!=CPU_TYPE_X86_64 ||
       h->ncmds>65536 || h->sizeofcmds>16*1024*1024 || !range(sizeof(*h),h->sizeofcmds,available))return false;
    size_t offset=sizeof(*h),end=offset+h->sizeofcmds;
    for(unsigned i=0;i<h->ncmds;i++) {
        if(!range(offset,sizeof(struct load_command),end))return false;
        const struct load_command *cmd=(const void *)((const char *)h+offset);
        if(cmd->cmdsize<8 || cmd->cmdsize%8 || !range(offset,cmd->cmdsize,end))return false;
        if(cmd->cmd==LC_SEGMENT_64 && cmd->cmdsize<sizeof(struct segment_command_64))return false;
        if(cmd->cmd==LC_UUID && cmd->cmdsize<sizeof(struct uuid_command))return false;
        if(cmd->cmd==LC_ID_DYLIB) {
            if(cmd->cmdsize<sizeof(struct dylib_command))return false;
            const struct dylib_command *d=(const void *)cmd;
            if(d->dylib.name.offset<sizeof(*d) || d->dylib.name.offset>=cmd->cmdsize ||
               !memchr((const char *)cmd+d->dylib.name.offset,0,cmd->cmdsize-d->dylib.name.offset))return false;
        }
        offset+=cmd->cmdsize;
    }
    return offset==end;
}
static void make_image(struct dyld_image_s *image,dyld_shared_cache_t cache,uint64_t address) {
    *image=(struct dyld_image_s){.magic=IMAGE_MAGIC,.address=address,.cache=cache};
    const struct mach_header_64 *h=vm_bytes(cache,address,sizeof(*h));
    if(!h || h->sizeofcmds>16*1024*1024)return;
    size_t extent=sizeof(*h)+h->sizeofcmds;
    h=vm_bytes(cache,address,extent);if(h && valid_header(h,extent))image->header=h;
}
void dyld_shared_cache_for_each_image(dyld_shared_cache_t cache,void (^block)(dyld_image_t)) {
    assert(cache && cache->magic==CACHE_MAGIC && block);
    const struct dyld_cache_image_text_info *images=(const void *)(cache->files[0].bytes+cache->header->imagesTextOffset);
    for(uint64_t i=0;i<cache->header->imagesTextCount;i++) {
        struct dyld_image_s image;make_image(&image,cache,images[i].loadAddress);block(&image);image.magic=0;
    }
}
static const struct load_command *image_command(dyld_image_t image,uint32_t kind) {
    assert(image && image->magic==IMAGE_MAGIC);if(!image->header)return NULL;
    const struct load_command *cmd=(const void *)(image->header+1);
    for(unsigned i=0;i<image->header->ncmds;i++) {
        if(cmd->cmd==kind)return cmd;cmd=(const void *)((const char *)cmd+cmd->cmdsize);
    }
    return NULL;
}
bool dyld_image_copy_uuid(dyld_image_t image,uuid_t *uuid) {
    assert(image && image->magic==IMAGE_MAGIC);
    if(image->process_image){if(!image->has_uuid)return false;memcpy(uuid,image->uuid,16);return true;}
    assert(uuid);const struct uuid_command *cmd=(const void *)image_command(image,LC_UUID);
    if(!cmd)return false;memcpy(uuid,cmd->uuid,16);return true;
}
const char *dyld_image_get_installname(dyld_image_t image) {
    const struct dylib_command *cmd=(const void *)image_command(image,LC_ID_DYLIB);
    return cmd?(const char *)cmd+cmd->dylib.name.offset:NULL;
}
const char *dyld_image_get_file_path(dyld_image_t image) {
    assert(image && image->magic==IMAGE_MAGIC);return image->process_image?image->file_path:NULL;
}
bool dyld_image_for_each_segment_info(dyld_image_t image,void (^block)(const char *,uint64_t,uint64_t,int)) {
    assert(image && image->magic==IMAGE_MAGIC && block);if(!image->header)return false;
    const struct load_command *cmd=(const void *)(image->header+1);
    for(unsigned i=0;i<image->header->ncmds;i++) {
        if(cmd->cmd==LC_SEGMENT_64) {
            const struct segment_command_64 *s=(const void *)cmd;char name[17];memcpy(name,s->segname,16);name[16]=0;
            if(image->process_image && image->header->filetype==MH_EXECUTE && !strcmp(name,"__PAGEZERO"))goto next_segment;
            block(name,s->vmaddr+image->slide,s->vmsize,s->initprot);
        }
next_segment:
        cmd=(const void *)((const char *)cmd+cmd->cmdsize);
    }
    return true;
}
bool dyld_image_content_for_segment(dyld_image_t image,const char *name,void (^block)(const void *,uint64_t,uint64_t)) {
    assert(image && image->magic==IMAGE_MAGIC && name && block);if(!image->header)return false;
    const struct load_command *cmd=(const void *)(image->header+1);
    for(unsigned i=0;i<image->header->ncmds;i++) {
        if(cmd->cmd==LC_SEGMENT_64) {
            const struct segment_command_64 *s=(const void *)cmd;
            if(strlen(name)<=16 && !strncmp(name,s->segname,16)) {
                if(image->process_image) {
                    if(!image->file_slice || !range(s->fileoff,s->filesize,image->file_length) || s->filesize>s->vmsize)return false;
                    if(image->header->filetype==MH_EXECUTE && !strcmp(name,"__PAGEZERO"))return false;
                    const void *bytes=image->file_slice+s->fileoff;void *temporary=NULL;
                    if(s->filesize<s->vmsize) {
                        if(s->vmsize>512*1024*1024){errno=ENOMEM;return false;}
                        temporary=calloc(1,s->vmsize);if(!temporary)return false;
                        memcpy(temporary,bytes,s->filesize);bytes=temporary;
                    }
                    block(bytes,s->vmaddr+image->slide,s->vmsize);free(temporary);return true;
                }
                const void *content=vm_bytes(image->cache,s->vmaddr,s->vmsize);
                if(!content)return false;block(content,s->vmaddr,s->vmsize);return true;
            }
        }
        cmd=(const void *)((const char *)cmd+cmd->cmdsize);
    }
    return false;
}
void dyld_for_each_installed_shared_cache_with_system_path(const char *root,void (^block)(dyld_shared_cache_t)) {
    assert(block);
    static const char *directories[]={
        "/System/Volumes/Preboot/Cryptexes/OS/System/Library/dyld/",
        "/System/Volumes/Preboot/Cryptexes/OS/System/DriverKit/System/Library/dyld/",
        "/private/preboot/Cryptexes/OS/System/Library/Caches/com.apple.dyld/",
        "/private/preboot/Cryptexes/OS/System/DriverKit/System/Library/dyld/",
        "/System/Cryptexes/OS/System/Library/Caches/com.apple.dyld/",
        "/System/Cryptexes/OS/System/Library/dyld/",
        "/System/Cryptexes/ExclaveOS/System/ExclaveKit/System/Library/dyld/",
        "/System/Volumes/Preboot/Cryptexes/Incoming/OS/System/Library/dyld/",
        "/System/Volumes/Preboot/Cryptexes/Incoming/OS/System/DriverKit/System/Library/dyld/",
        "/private/preboot/Cryptexes/Incoming/OS/System/Library/Caches/com.apple.dyld/",
        "/private/preboot/Cryptexes/Incoming/OS/System/DriverKit/System/Library/dyld/",
        "/System/Cryptexes/Incoming/OS/System/Library/Caches/com.apple.dyld/",
        "/System/Cryptexes/Incoming/OS/System/Library/dyld/",
        "/System/Library/Caches/com.apple.dyld/","/System/DriverKit/System/Library/dyld/",
        "/System/ExclaveKit/System/Library/dyld/","/System/Library/dyld/"};
    char visited[17][PATH_MAX];unsigned count=0;
    for(unsigned i=0;i<sizeof(directories)/sizeof(directories[0]);i++) {
        char path[PATH_MAX],canonical[PATH_MAX];
        if(snprintf(path,sizeof(path),"%s%s",root?root:"",directories[i])>=(int)sizeof(path) || !realpath(path,canonical))continue;
        bool duplicate=false;for(unsigned j=0;j<count;j++)if(!strcmp(visited[j],canonical))duplicate=true;
        if(duplicate)continue;strlcpy(visited[count++],canonical,PATH_MAX);
        DIR *directory=opendir(canonical);if(!directory)continue;
        struct dirent *entry;
        while((entry=readdir(directory))) {
            if(entry->d_type!=DT_REG)continue;
            const char *dot=strchr(entry->d_name,'.');if(dot && strcmp(dot,".development"))continue;
            if(snprintf(path,sizeof(path),"%s/%s",canonical,entry->d_name)>=(int)sizeof(path))continue;
            dyld_shared_cache_for_file(path,block);
        }
        closedir(directory);
    }
}
void dyld_for_each_installed_shared_cache(void (^block)(dyld_shared_cache_t)) {
    dyld_for_each_installed_shared_cache_with_system_path("/",block);
}

static bool header_uuid(const struct mach_header_64 *h,uint8_t uuid[16]) {
    const struct load_command *cmd=(const void *)(h+1);
    for(unsigned i=0;i<h->ncmds;i++) {
        if(cmd->cmd==LC_UUID){memcpy(uuid,((const struct uuid_command *)cmd)->uuid,16);return true;}
        cmd=(const void *)((const char *)cmd+cmd->cmdsize);
    }
    return false;
}
static uint32_t be32(const unsigned char *p){uint32_t n;memcpy(&n,p,4);return __builtin_bswap32(n);}
static uint64_t be64(const unsigned char *p){uint64_t n;memcpy(&n,p,8);return __builtin_bswap64(n);}
static bool select_file_slice(struct dyld_image_s *image,const unsigned char *bytes,size_t length) {
    const struct mach_header_64 *h=(const void *)bytes;uint8_t id[16];
    if(!valid_header(h,length))return false;
    if(image->has_uuid && (!header_uuid(h,id) || memcmp(id,image->uuid,16)))return false;
    image->file_slice=bytes;image->file_length=length;
    if(!image->header)image->header=h;
    return true;
}
static void map_image_file(struct dyld_image_s *image,const char *path) {
    if(!path)return;
    int fd=open(path,O_RDONLY);if(fd<0)return;
    struct stat status;
    if(fstat(fd,&status) || !S_ISREG(status.st_mode) || status.st_size<32 ||
       (uint64_t)status.st_size>UINT64_C(16)*1024*1024*1024){close(fd);return;}
    size_t length=status.st_size;unsigned char *bytes=mmap(NULL,length,PROT_READ,MAP_PRIVATE,fd,0);close(fd);
    if(bytes==MAP_FAILED)return;
    bool selected=false;
    if(!memcmp(bytes,"\xca\xfe\xba\xbe",4) || !memcmp(bytes,"\xca\xfe\xba\xbf",4)) {
        bool fat64=bytes[3]==0xbf;unsigned stride=fat64?32:20,count=be32(bytes+4);
        if(count<=128 && range(8,(size_t)count*stride,length))for(unsigned i=0;i<count;i++) {
            const unsigned char *arch=bytes+8+i*stride;if(be32(arch)!=CPU_TYPE_X86_64)continue;
            uint64_t offset=fat64?be64(arch+8):be32(arch+8),size=fat64?be64(arch+16):be32(arch+12);
            if(range(offset,size,length) && select_file_slice(image,bytes+offset,size)){selected=true;break;}
        }
    } else selected=select_file_slice(image,bytes,length);
    if(!selected){munmap(bytes,length);return;}
    image->file_mapping=bytes;image->file_mapping_size=length;image->file_path=path;
}
static void make_process_image(struct dyld_image_s *image,task_t task,uint64_t address,const uint8_t uuid[16],const char *path) {
    *image=(struct dyld_image_s){.magic=IMAGE_MAGIC,.address=address,.process_image=true};
    if(uuid){memcpy(image->uuid,uuid,16);for(unsigned i=0;i<16;i++)image->has_uuid|=uuid[i]!=0;}
    struct mach_header_64 h;mach_vm_size_t copied=0;
    if(mach_vm_read_overwrite(task,address,sizeof(h),(mach_vm_address_t)&h,&copied)==KERN_SUCCESS &&
       copied==sizeof(h) && h.magic==MH_MAGIC_64 && h.sizeofcmds<=16*1024*1024) {
        size_t extent=sizeof(h)+h.sizeofcmds;void *buffer=malloc(extent);
        if(buffer) {
            if(mach_vm_read_overwrite(task,address,extent,(mach_vm_address_t)buffer,&copied)==KERN_SUCCESS &&
               copied==extent && valid_header(buffer,extent)){image->header=buffer;image->owned_header=buffer;}
            else free(buffer);
        }
    }
    map_image_file(image,path);
    if(image->header) {
        const struct load_command *cmd=(const void *)(image->header+1);
        for(unsigned i=0;i<image->header->ncmds;i++) {
            if(cmd->cmd==LC_SEGMENT_64) {
                const struct segment_command_64 *segment=(const void *)cmd;
                if(!strncmp(segment->segname,"__TEXT",16)){image->slide=address-segment->vmaddr;break;}
            }
            cmd=(const void *)((const char *)cmd+cmd->cmdsize);
        }
    }
}
dyld_process_t dyld_process_create_for_task(task_read_t task,kern_return_t *error) {
    kern_return_t result=KERN_FAILURE;dyld_process_info info=_dyld_process_info_create(task,0,&result);
    if(!info){if(error)*error=result==KERN_SUCCESS?KERN_FAILURE:result;return NULL;}
    _dyld_process_info_release(info);
    result=mach_port_mod_refs(mach_task_self(),task,MACH_PORT_RIGHT_SEND,1);
    if(result!=KERN_SUCCESS){if(error)*error=result;return NULL;}
    struct dyld_process_s *process=calloc(1,sizeof(*process));
    if(!process){mach_port_deallocate(mach_task_self(),task);if(error)*error=KERN_RESOURCE_SHORTAGE;return NULL;}
    process->magic=PROCESS_MAGIC;process->task=task;if(error)*error=KERN_SUCCESS;return process;
}
dyld_process_t dyld_process_create_for_current_task(void){return dyld_process_create_for_task(mach_task_self(),NULL);}
void dyld_process_dispose(dyld_process_t process) {
    if(!process)return;assert(process->magic==PROCESS_MAGIC);process->magic=0;
    mach_port_deallocate(mach_task_self(),process->task);free(process);
}
dyld_process_snapshot_t dyld_process_snapshot_create_for_process(dyld_process_t process,kern_return_t *error) {
    assert(process && process->magic==PROCESS_MAGIC);
    kern_return_t result=KERN_FAILURE;dyld_process_info info=_dyld_process_info_create(process->task,0,&result);
    if(!info){if(error)*error=result==KERN_SUCCESS?KERN_FAILURE:result;return NULL;}
    result=mach_port_mod_refs(mach_task_self(),process->task,MACH_PORT_RIGHT_SEND,1);
    if(result!=KERN_SUCCESS){_dyld_process_info_release(info);if(error)*error=result;return NULL;}
    struct dyld_process_snapshot_s *snapshot=calloc(1,sizeof(*snapshot));
    if(!snapshot){_dyld_process_info_release(info);mach_port_deallocate(mach_task_self(),process->task);
        if(error)*error=KERN_RESOURCE_SHORTAGE;return NULL;}
    snapshot->magic=SNAPSHOT_MAGIC;snapshot->info=info;snapshot->task=process->task;
    if(error)*error=KERN_SUCCESS;return snapshot;
}
void dyld_process_snapshot_dispose(dyld_process_snapshot_t snapshot) {
    if(!snapshot)return;assert(snapshot->magic==SNAPSHOT_MAGIC);snapshot->magic=0;
    _dyld_process_info_release(snapshot->info);mach_port_deallocate(mach_task_self(),snapshot->task);free(snapshot);
}
dyld_shared_cache_t dyld_process_snapshot_get_shared_cache(dyld_process_snapshot_t snapshot) {
    assert(snapshot && snapshot->magic==SNAPSHOT_MAGIC);
    dyld_process_cache_info info;_dyld_process_info_get_cache(snapshot->info,&info);
    if(info.noCache || !info.cacheBaseAddress)return NULL;
    fputs("Live shared-cache process snapshots are unsupported by this Darling adapter\n",stderr);abort();
}
void dyld_process_snapshot_for_each_image(dyld_process_snapshot_t snapshot,void (^block)(dyld_image_t)) {
    assert(snapshot && snapshot->magic==SNAPSHOT_MAGIC && block);
    if(dyld_process_snapshot_get_shared_cache(snapshot))abort();
    _dyld_process_info_for_each_image(snapshot->info,^(uint64_t address,const uuid_t uuid,const char *path) {
        struct dyld_image_s image;make_process_image(&image,snapshot->task,address,uuid,path);
        block(&image);image.magic=0;
        if(image.file_mapping)munmap(image.file_mapping,image.file_mapping_size);
        free(image.owned_header);
    });
}
