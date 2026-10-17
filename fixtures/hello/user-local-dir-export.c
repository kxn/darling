#include <assert.h>
#include <dlfcn.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>
typedef char *(*directory_fn)(uid_t, int, char *, size_t);
int main(int argc, char **argv) {
    assert(argc == 3); setbuf(stdout, NULL);
    void *system = dlopen(argv[1], RTLD_LAZY | RTLD_LOCAL);
    assert(system);
    directory_fn forwarded = (directory_fn)dlsym(system, "__user_local_dirname");
    assert(forwarded);
    unsigned succeeded = 0, failed = 0;
    for (int which = 0; which <= 4; which++) {
        const size_t lengths[] = {1024, 1, 8};
        for (unsigned k = 0; k < 3; k++) {
            struct { uint64_t before; char path[1024]; uint64_t after; } a, b;
            memset(&a, 0xa7, sizeof(a)); memset(&b, 0xa7, sizeof(b));
            errno = 0;
            char *actual = forwarded(getuid(), which, a.path, lengths[k]);
            int actual_error = errno;
            void *native = dlopen(argv[2], RTLD_LAZY | RTLD_LOCAL); assert(native);
            directory_fn direct = (directory_fn)dlsym(native, "__user_local_dirname"); assert(direct && direct != forwarded);
            Dl_info owner;
            assert(dladdr((void *)direct, &owner) && !strcmp(owner.dli_fname, argv[2]));
            errno = 0; char *expected = direct(getuid(), which, b.path, lengths[k]);
            int expected_error = errno;
            assert((actual != NULL) == (expected != NULL));
            assert(actual_error == expected_error);
            assert(!memcmp(&a, &b, sizeof(a)));
            assert(a.before == UINT64_C(0xa7a7a7a7a7a7a7a7) && a.after == a.before);
            if (actual) {
                assert(actual == a.path && expected == b.path && a.path[0] == '/');
                assert(strlen(a.path) < lengths[k]); succeeded++;
            } else failed++;
        }
    }
    printf("ORIGINAL_USER_DIRECTORY_NAMED_EXPORT_DIRECT_ABI_BOUNDS_AND_ERRNO_OK %u %u\n", succeeded, failed);
    return 0;
}
