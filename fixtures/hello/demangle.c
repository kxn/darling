#include <assert.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    void *image = dlopen("/usr/lib/swift/libswiftDemangle.dylib", RTLD_NOW);
    if (!image) { fprintf(stderr, "%s\n", dlerror()); return 1; }
    typedef size_t (*Demangler)(const char *, char *, size_t);
    Demangler full = dlsym(image, "swift_demangle_getDemangledName");
    Demangler module = dlsym(image, "swift_demangle_getModuleName");
    Demangler simple = dlsym(image, "swift_demangle_getSimplifiedDemangledName");
    assert(full && module && simple);
    char buffer[512];
    assert(full("$s7Combine4JustVMa", buffer, sizeof(buffer)) > 0);
    assert(strstr(buffer, "Combine.Just"));
    assert(module("$s4main3fooyyF", buffer, sizeof(buffer)) == 4);
    assert(strcmp(buffer, "main") == 0);
    assert(simple("$s7Combine4JustVMa", buffer, sizeof(buffer)) > 0);
    assert(full("not_a_swift_symbol", buffer, sizeof(buffer)) == 0);
    puts("ORIGINAL_APPLE_DEMANGLER_OK");
}
