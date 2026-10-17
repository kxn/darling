#include <assert.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <mach-o/utils.h>
#include <mach-o/loader.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static unsigned mapped_fixtures(void) {
    FILE* maps = fopen("/Volumes/SystemRoot/proc/self/maps", "r"); assert(maps);
    char line[4096]; unsigned count = 0;
    while (fgets(line, sizeof(line), maps)) if (strstr(line, "/macho-slices-source/fixtures/")) ++count;
    fclose(maps); return count;
}
int main(int argc, char** argv) {
    assert(argc == 3); setbuf(stdout, NULL);
    const char* names[] = {"thin32", "thin64", "fat32", "fat64", "hidden32", "maximum-hidden32"};
    for (unsigned i = 0; i < 6; ++i) {
        char path[1024]; snprintf(path, sizeof(path), "%s/%s", argv[1], names[i]);
        __block unsigned count = 0;
        assert(!macho_for_each_slice(path, ^(const struct mach_header* header, uint64_t offset, size_t size, bool* stop) {
            assert(header && size >= sizeof(struct mach_header) && !*stop);
            assert(header->magic == MH_MAGIC || header->magic == MH_MAGIC_64);
            if (i < 2) assert(offset == 0);
            else assert(offset == (uint64_t)(count + 1) * 0x1000);
            ++count;
        }));
        assert(count == (i < 2 ? 1 : i == 5 ? 17 : 2));
        assert(!macho_for_each_slice(path, NULL));
        int fd = open(path, O_RDONLY); assert(fd >= 0 && lseek(fd, 7, SEEK_SET) == 7);
        count = 0;
        assert(!macho_for_each_slice_in_fd(fd, ^(const struct mach_header* header, uint64_t offset, size_t size, bool* stop) {
            (void)header; (void)offset; (void)size; ++count; *stop = true;
        }));
        assert(count == 1 && lseek(fd, 0, SEEK_CUR) == 7);
        assert(!close(fd));
    }
    char path[1024];
    snprintf(path, sizeof(path), "%s/random", argv[1]);
    assert(macho_for_each_slice(path, NULL) == EFTYPE);
    snprintf(path, sizeof(path), "%s/absent", argv[1]);
    assert(macho_for_each_slice(path, NULL) == ENOENT);
    assert(macho_for_each_slice_in_fd(-1, NULL) == EBADF);
    snprintf(path, sizeof(path), "%s/thin64", argv[1]);
    assert(!chmod(path, 0000));
    assert(macho_for_each_slice(path, NULL) == EACCES);
    assert(!chmod(path, 0644));
    const char* bad[] = {"too-many", "bounds", "duplicate", "overlap", "wrong-cpu", "unaligned"};
    unsigned baseline = mapped_fixtures();
    for (unsigned cycle = 0; cycle < 64; ++cycle) {
        for (unsigned i = 0; i < sizeof(bad)/sizeof(*bad); ++i) {
            snprintf(path, sizeof(path), "%s/%s", argv[1], bad[i]);
            __block unsigned count = 0;
            assert(macho_for_each_slice(path, ^(const struct mach_header* h, uint64_t o, size_t s, bool* stop) {
                (void)h; (void)o; (void)s; (void)stop; ++count;
            }) == EBADMACHO);
            assert(!count);
        }
    }
    assert(mapped_fixtures() == baseline);
    __block unsigned count = 0; __block bool intel = false;
    assert(!macho_for_each_slice(argv[2], ^(const struct mach_header* header, uint64_t offset, size_t size, bool* stop) {
        assert(size > sizeof(struct mach_header_64) && !*stop);
        assert(header->magic == MH_MAGIC_64);
        if (header->cputype == CPU_TYPE_X86_64) intel = true;
        assert(offset); ++count;
    }));
    assert(intel && count >= 2);
    printf("APPLE_MACHO_SLICE_UTILITIES_THIN_FAT32_FAT64_STOP_FD_ERRORS_384_BAD_FILES_NO_MAPPING_LEAK_AND_ACTUAL_XCODE_OK %u\n", count);
    return 0;
}
