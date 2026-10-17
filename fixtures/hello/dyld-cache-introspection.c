#include <TargetConditionals.h>
#include <uuid/uuid.h>
#include <mach-o/dyld_introspection.h>
#include <assert.h>
#include <dlfcn.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include "../../runtime/dyld-cache-introspection/oracle.h"

static void inspect(dyld_shared_cache_t cache) {
    uuid_t actual;dyld_shared_cache_copy_uuid(cache,&actual);assert(!memcmp(actual,cache_uuid,16));
    assert(dyld_shared_cache_get_base_address(cache)==CACHE_BASE);
    assert(dyld_shared_cache_get_mapped_size(cache)==CACHE_SIZE);
    assert(dyld_shared_cache_is_mapped_private(cache));
    __block unsigned files=0,images=0,selected=0;
    dyld_shared_cache_for_each_file(cache,^(const char *path) {
        assert(path && strstr(path,"dyld_shared_cache_x86_64h"));files++;
    });
    assert(files==CACHE_FILES);
    dyld_shared_cache_for_each_image(cache,^(dyld_image_t image) {
        images++;assert(dyld_image_get_file_path(image)==NULL);
        const char *name=dyld_image_get_installname(image);
        assert(images<=CACHE_IMAGES && (name!=NULL)==expected_image_has_name[images-1]);
        uuid_t id;assert(dyld_image_copy_uuid(image,&id));
        assert(!memcmp(id,expected_image_uuids[images-1],16));
        if(!name)return;
        if(strcmp(name,SELECTED_IMAGE))return;
        selected++;assert(!memcmp(id,image_uuid,16));
        __block unsigned segments=0;
        assert(dyld_image_for_each_segment_info(image,^(const char *segment,uint64_t address,uint64_t size,int permission) {
            assert(segments<sizeof(expected_segments)/sizeof(expected_segments[0]));
            const struct ExpectedSegment *expected=expected_segments+segments++;
            assert(!strcmp(segment,expected->name) && address==expected->address && size==expected->size);
            assert(permission>=0 && permission<=7);
        }));
        assert(segments==sizeof(expected_segments)/sizeof(expected_segments[0]));
        __block unsigned content=0;
        assert(dyld_image_content_for_segment(image,"__TEXT",^(const void *bytes,uint64_t address,uint64_t size) {
            assert(address==expected_segments[0].address && size==expected_segments[0].size);
            assert(size>=sizeof(image_prefix) && !memcmp(bytes,image_prefix,sizeof(image_prefix)));content++;
        }));
        assert(content==1);
        assert(!dyld_image_content_for_segment(image,"__NO_SUCH_SEGMENT",^(const void *p,uint64_t a,uint64_t s) { assert(false); }));
    });
    assert(images==CACHE_IMAGES && selected==1);
}
int main(int argc,char **argv) {
    if(argc!=7)return 2;
    void *system=dlopen("/usr/lib/libSystem.B.dylib",RTLD_LAZY|RTLD_LOCAL);assert(system);
    assert(dlsym(system,"dyld_shared_cache_for_file")==dyld_shared_cache_for_file);
    Dl_info owner;assert(dladdr((void *)dyld_shared_cache_for_file,&owner));
    assert(strstr(owner.dli_fname,"/native-library-stage/libDarlingCacheIntrospection.dylib"));
    __block unsigned count=0;
    dyld_for_each_installed_shared_cache(^(dyld_shared_cache_t c) {count++;});assert(count==0);
    dyld_for_each_installed_shared_cache_with_system_path(argv[3],^(dyld_shared_cache_t c) {count++;});assert(count==0);
    assert(!dyld_shared_cache_for_file(argv[4],^(dyld_shared_cache_t c) {assert(false);}));
    assert(!dyld_shared_cache_for_file(argv[5],^(dyld_shared_cache_t c) {assert(false);}));
    assert(!dyld_shared_cache_for_file(argv[6],^(dyld_shared_cache_t c) {assert(false);}));
    assert(!dyld_shared_cache_for_file("/no-such-linuxcode-cache-file",^(dyld_shared_cache_t c) {assert(false);}));
    assert(dyld_shared_cache_for_file(argv[1],^(dyld_shared_cache_t c) {inspect(c);count++;}));assert(count==1);
    count=0;
    dyld_for_each_installed_shared_cache_with_system_path(argv[2],^(dyld_shared_cache_t c) {inspect(c);count++;});
    assert(count==1); /* Two directory aliases must enumerate the cache once. */
    puts("REAL_SPLIT_INTEL_CACHE_UUID_FILES_IMAGES_SEGMENTS_CONTENT_EMPTY_BAD_INPUT_DEDUP_OK");
    return 0;
}
