#include <assert.h>
#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
typedef int (*mkdir_fn)(const char *, mode_t, const char *);
int main(int argc, char **argv) {
    assert(argc == 3); setbuf(stdout, NULL);
    void *system = dlopen(argv[1], RTLD_LAZY | RTLD_LOCAL); assert(system);
    mkdir_fn forwarded = (mkdir_fn)dlsym(system, "rootless_mkdir_datavault"); assert(forwarded);
    char base[] = "/Volumes/SystemRoot/workspace/artifacts/datavault-test-XXXXXX";
    assert(mkdtemp(base));
    char path[1024];
    unsigned succeeded = 0, failed = 0;
    for (unsigned k = 0; k < 4; k++) {
        snprintf(path, sizeof(path), "%s/%s", base, k == 0 ? "missing/child" : "entry");
        int results[2], errors[2], exists[2]; unsigned flags[2];
        for (unsigned direct_call = 0; direct_call < 2; direct_call++) {
            if (k == 2) { FILE *file = fopen(path, "w"); assert(file); fclose(file); }
            if (k == 3) assert(mkdir(path, 0700) == 0);
            mkdir_fn target = forwarded;
            if (direct_call) {
                void *native = dlopen(argv[2], RTLD_LAZY | RTLD_LOCAL); assert(native);
                target = (mkdir_fn)dlsym(native, "rootless_mkdir_datavault");
                Dl_info owner;
                assert(target && target != forwarded && dladdr((void *)target, &owner));
                assert(!strcmp(owner.dli_fname, argv[2]));
            }
            errno = 0; results[direct_call] = target(path, 0700, k % 2 ? "com.apple.LaunchServices" : NULL);
            errors[direct_call] = errno;
            struct stat st; exists[direct_call] = lstat(path, &st) == 0;
            flags[direct_call] = exists[direct_call] ? st.st_flags : 0;
            if (results[direct_call] == 0) assert(exists[direct_call] && (flags[direct_call] & 0x80));
            if (exists[direct_call]) {
                assert(!(flags[direct_call] & 0x80)); /* This backend currently has no data-vault policy. */
                assert((k == 2 ? unlink(path) : rmdir(path)) == 0);
            }
        }
        assert(results[0] == results[1] && errors[0] == errors[1]);
        assert(exists[0] == exists[1] && flags[0] == flags[1]);
        if (results[0] == 0) succeeded++; else { assert(results[0] == -1 && errors[0]); failed++; }
        printf("DATAVAULT_CASE %u result=%d errno=%d remaining=%d flags=%x\n", k, results[0], errors[0], exists[0], flags[0]);
    }
    assert(rmdir(base) == 0);
    printf("ORIGINAL_DATAVAULT_NAMED_EXPORT_DIRECT_ERRORS_AND_FILESYSTEM_EFFECTS_OK %u %u\n", succeeded, failed);
}
