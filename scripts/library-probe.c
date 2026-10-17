#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
int main(int argc, char** argv) {
    int lazy = argc == 3 && strcmp(argv[1], "--lazy") == 0;
    if (argc != 2 && !lazy) return 2;
    void* image = dlopen(argv[lazy ? 2 : 1], lazy ? RTLD_LAZY : RTLD_NOW);
    if (!image) {
        fprintf(stderr, "%s\n", dlerror());
        return 1;
    }
    puts(lazy ? "Library loaded (RTLD_LAZY)" : "Library loaded");
    return 0;
}
