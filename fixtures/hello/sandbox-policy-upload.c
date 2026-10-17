#include <dlfcn.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

struct compiled_profile { const char *builtin; const void *data; uint64_t length; };
static unsigned checks, uploads;
#define CHECK(x) do { checks++; if (!(x)) { fprintf(stderr,"FAIL line=%d expression=%s errno=%d\n",__LINE__,#x,errno); exit(1); } } while (0)
static int (*mac)(const char *, int, void *);
static int (*query)(int, const char *, int, ...);
static int (*apply)(struct compiled_profile *);
static void raw(uint64_t *args, int error) {
    errno = 0;
    CHECK(mac("Sandbox",0,args) == -1 && errno == error);
    CHECK(query(getpid(),NULL,0) == 0);
}
int main(int argc, char **argv) {
    setbuf(stdout,NULL); CHECK(argc > 1);
    mac = dlsym(RTLD_DEFAULT,"__mac_syscall");
    query = dlsym(RTLD_DEFAULT,"sandbox_check");
    CHECK(mac && query);
    void *lib = dlopen("/usr/lib/libsandbox.1.dylib",RTLD_LAZY|RTLD_LOCAL); CHECK(lib);
    void *(*create)(void) = dlsym(lib,"sandbox_create_params");
    int (*set)(void *,const char *,const char *) = dlsym(lib,"sandbox_set_param");
    void (*destroy)(void *) = dlsym(lib,"sandbox_free_params");
    struct compiled_profile *(*compile)(const char *,void *,char **) = dlsym(lib,"sandbox_compile_string");
    struct compiled_profile *(*named)(const char *,void *,char **) = dlsym(lib,"sandbox_compile_named");
    void (*release)(void *) = dlsym(lib,"sandbox_free_profile");
    apply = dlsym(lib,"sandbox_apply"); CHECK(create && set && destroy && compile && named && release && apply);
    void *params = create(); CHECK(params);
    CHECK(set(params,"DARWIN_USER_TEMP_DIR","/tmp/com.apple.coreservicesd") == 0);
    CHECK(set(params,"DARWIN_USER_CACHE_DIR","/root/.cache/com.apple.coreservicesd") == 0);
    for (unsigned i=0;i<3;i++) {
        char *error = NULL;
        struct compiled_profile *p = i == 2 ? named("com.apple.coreservicesd",params,&error)
            : compile(i ? "(version 1)(deny default)" : "(version 1)(allow default)",params,&error);
        CHECK(p && !p->builtin && p->data && p->length >= 16);
        errno=0; CHECK(apply(p) == -1 && errno == ENOTSUP);
        CHECK(query(getpid(),NULL,0) == 0);
        printf("NATIVE_SANDBOX_UPLOAD_REJECTED_UNENFORCED name=%s bytes=%llu\n",
            i==2 ? "coreservicesd" : i ? "deny-all" : "allow-all",(unsigned long long)p->length);
        release(p); free(error); uploads++;
    }
    destroy(params);
    for (int i=1;i<argc;i++) {
        FILE *file=fopen(argv[i],"rb"); CHECK(file);
        CHECK(fseek(file,0,SEEK_END)==0); long length=ftell(file); CHECK(length>=16 && length<=1024*1024);
        rewind(file); void *data=malloc(length); CHECK(data);
        CHECK(fread(data,1,length,file)==(size_t)length && fclose(file)==0);
        uint64_t args[4]={(uintptr_t)data,(uint64_t)length,0,0};
        raw(args,ENOTSUP); free(data); uploads++;
    }
    uint8_t malformed[432]={0};
    uint64_t args[4]={(uintptr_t)malformed,sizeof malformed,0,0};
    raw(args,EINVAL);
    args[0]=1; raw(args,EFAULT);
    args[0]=0; raw(args,EFAULT);
    args[0]=UINT64_MAX-1; raw(args,EFAULT);
    args[0]=(uintptr_t)malformed; args[1]=0; raw(args,EINVAL);
    args[1]=1024*1024+1; raw(args,EINVAL);
    args[1]=sizeof malformed; args[2]=(uintptr_t)"container"; args[3]=10; raw(args,ENOTSUP);
    raw((uint64_t *)1,EFAULT); raw(NULL,EFAULT);
    printf("SANDBOX_UPLOAD_NATIVE_ABI_AND_ATOMIC_FAILURE_OK checks=%u uploads=%u\n",checks,uploads);
    return 0;
}
