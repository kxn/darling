// RawImagePatch argument ABI also used by blacktop/ipsw/pkg/ota/ridiff.
#include <stdint.h>
#include <dlfcn.h>
#include <stdio.h>

struct RawImage {
    int64_t progress_function;
    int64_t progress_context;
    const char *input;
    const char *output;
    const char *patch;
    uint32_t not_cryptex_cache;
    uint32_t threads;
    uint32_t verbose;
};
int main(int argc, char **argv) {
    if (argc != 4) return 2;
    setbuf(stdout,NULL);setbuf(stderr,NULL);
    void *image=dlopen(argv[1],RTLD_LAZY|RTLD_LOCAL);
    if (!image) {fprintf(stderr,"%s\n",dlerror());return 1;}
    int32_t (*apply)(struct RawImage *)=dlsym(image,"RawImagePatch");
    if (!apply) {fprintf(stderr,"%s\n",dlerror());return 1;}
    struct RawImage args={0,0,"",argv[3],argv[2],0,2,2};
    int32_t result=apply(&args);
    printf("RawImagePatch returned %d\n",result);
    return result==0?0:1;
}
