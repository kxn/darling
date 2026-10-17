#include <assert.h>
#include <dlfcn.h>
#include <errno.h>
#include <mach/message.h>
#include <mach-o/loader.h>
#include <malloc/malloc.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

struct api {
    char* (*file)(const char*, const char*, uint32_t);
    char* (*process)(const char*, const char*, uint32_t, audit_token_t);
    char* (*pid)(const char*, const char*, uint32_t, pid_t);
    char* (*self)(const char*, const char*, uint32_t);
    int64_t (*consume)(const char*);
    int (*release)(int64_t);
};

static struct api load_api(void* library) {
    return (struct api){
        dlsym(library, "sandbox_extension_issue_file"),
        dlsym(library, "sandbox_extension_issue_file_to_process"),
        dlsym(library, "sandbox_extension_issue_file_to_process_by_pid"),
        dlsym(library, "sandbox_extension_issue_file_to_self"),
        dlsym(library, "sandbox_extension_consume"),
        dlsym(library, "sandbox_extension_release")};
}

static void assert_uuid(void* symbol, const char* expected) {
    Dl_info owner;
    assert(dladdr(symbol, &owner));
    const struct mach_header_64* header = owner.dli_fbase;
    assert(header->magic == MH_MAGIC_64);
    const struct load_command* lc = (const void*)(header + 1);
    for (unsigned i = 0; i < header->ncmds; ++i) {
        if (lc->cmd == LC_UUID) {
            char text[33];
            const struct uuid_command* u = (const void*)lc;
            for (unsigned j = 0; j < 16; ++j) snprintf(text + j * 2, 3, "%02x", u->uuid[j]);
            assert(!strcmp(text, expected));
            return;
        }
        lc = (const void*)((const char*)lc + lc->cmdsize);
    }
    assert(!"Missing sandbox UUID");
}

static void compare_constants(void* source, void* native) {
    const char* classes[] = {"APP_SANDBOX_READ", "APP_SANDBOX_READ_WRITE", "APP_SANDBOX_MACH", "APP_SANDBOX_IOKIT_CLIENT"};
    for (unsigned i = 0; i < 4; ++i) {
        const char* const* left = dlsym(source, classes[i]);
        const char* const* right = dlsym(native, classes[i]);
        assert(left && right && *left && *right && !strcmp(*left, *right));
        assert(!strncmp(*left, "com.apple.app-sandbox.", 21));
    }
    const char* flags[] = {"SANDBOX_EXTENSION_DEFAULT", "SANDBOX_EXTENSION_CANONICAL", "SANDBOX_EXTENSION_PREFIXMATCH", "SANDBOX_EXTENSION_NO_REPORT"};
    uint32_t expected[] = {0, 2, 4, 16};
    for (unsigned i = 0; i < 4; ++i) {
        const uint32_t* left = dlsym(source, flags[i]);
        const uint32_t* right = dlsym(native, flags[i]);
        assert(left && right && *left == *right && *left == expected[i]);
    }
    puts("SANDBOX_NATIVE_FOUR_POINTER_CLASSES_AND_FOUR_UINT32_FLAGS_MATCH_OK");
}

int main(int argc, char** argv) {
    assert(argc == 3);
    void* source = dlopen("/usr/lib/system/libsystem_sandbox.dylib", RTLD_NOW | RTLD_LOCAL);
    assert(source);
    struct api a = load_api(source);
    if (!a.file || !a.process || !a.pid || !a.self || !a.consume || !a.release) {
        fprintf(stderr, "SOURCE_SANDBOX_LIBRARY_REJECTED\n");
        return 88;
    }
    assert_uuid(a.file, argv[1]);
    puts("SANDBOX_SOURCE_LIBRARY_UUID_VERIFIED"); fflush(stdout);
    void* native = dlopen(argv[2], RTLD_LAZY | RTLD_LOCAL);
    if (!native) fprintf(stderr, "%s\n", dlerror());
    assert(native);
    struct api b = load_api(native);
    assert(b.file && b.process && b.pid && b.self && b.consume && b.release);
    Dl_info owner;
    assert(dladdr(b.file, &owner));
    char* actual = realpath(owner.dli_fname, NULL), *expected = realpath(argv[2], NULL);
    assert(actual && expected && !strcmp(actual, expected)); free(actual); free(expected);
    compare_constants(source, native);
    const char* extension_class = *(const char* const*)dlsym(source, "APP_SANDBOX_READ");
    audit_token_t token = {{0}};
    token.val[5] = getpid(); token.val[7] = 12345;
    for (unsigned i = 0; i < 32; ++i) {
        uint32_t flags = (i & 1 ? 2u : 0u) | (i & 2 ? 4u : 0u) | (i & 4 ? 16u : 0u) | (i & 8 ? 0x30000u : 0u);
        errno = EDOM; char* left = a.file(extension_class, "/tmp", flags); int le = errno;
        errno = EDOM; char* right = b.file(extension_class, "/tmp", flags); int re = errno;
        assert(!left && !right && le == 103 && re == le); // actual ENOPOLICY
        errno = EDOM; left = a.process(extension_class, "/tmp", flags, token); le = errno;
        errno = EDOM; right = b.process(extension_class, "/tmp", flags, token); re = errno;
        assert(!left && !right && le == 103 && re == le);
        errno = EDOM; left = a.pid(extension_class, "/tmp", flags, getpid()); le = errno;
        errno = EDOM; right = b.pid(extension_class, "/tmp", flags, getpid()); re = errno;
        assert(!left && !right && le == 103 && re == le);
        errno = EDOM; left = a.self(extension_class, "/tmp", flags); le = errno;
        errno = EDOM; right = b.self(extension_class, "/tmp", flags); re = errno;
        assert(!left && !right && le == 103 && re == le);
        // The original user-space flag-1 path bypasses the kernel and returns
        // an unresolved marker, not a permission grant. Bytes beyond the C
        // string are uninitialized in the native malloc/strlcpy implementation.
        errno = EDOM; left = a.process(NULL, NULL, flags | 1, token); le = errno;
        errno = EDOM; right = b.process(NULL, NULL, flags | 1, token); re = errno;
        assert(left && right && left != right && le == EDOM && re == le);
        assert(malloc_size(left) >= 0x3ff0 && malloc_size(right) >= 0x3ff0);
        assert(!strcmp(left, right) && !strcmp(left, "invalid"));
        errno = EDOM; assert(a.consume(left) == 0 && errno == EDOM);
        errno = EDOM; assert(b.consume(right) == 0 && errno == EDOM);
        free(left); free(right);
    }
    for (unsigned i = 0; i < 32; ++i) {
        errno = EDOM; int64_t left = a.consume("unissued-token"); int le = errno;
        errno = EDOM; int64_t right = b.consume("unissued-token"); int re = errno;
        assert(left == -1 && right == -1 && le == 103 && re == le);
        errno = EDOM; int lr = a.release(i); le = errno;
        errno = EDOM; int rr = b.release(i); re = errno;
        assert(lr == -1 && rr == -1 && le == 103 && re == le);
    }
    puts("SANDBOX_NATIVE_128_ISSUE_32_UNRESOLVED_32_CONSUME_32_RELEASE_ABI_AND_REAL_MISSING_POLICY_ERRORS_MATCH_OK");
    puts("SANDBOX_MAC_POLICY_AND_REAL_POSITIVE_TOKEN_GRANTS_REMAIN_UNIMPLEMENTED");
    return 0;
}
