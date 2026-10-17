/* Test-only translation-unit override: all actual path preparation and syscall
 * code stays in the production source. Only the query transport is replaced. */
#define dserver_rpc_mac_syscall sandbox_fs_test_rpc
#include "../../vendor/darling/src/external/xnu/darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/helper/misc/sandbox_fs.c"
#undef dserver_rpc_mac_syscall
#include <darling/emulation/conversion/common_at.h>
extern int dserver_rpc_mac_syscall(const char *,int32_t,void *,int32_t *);
static int equal(const char *a,const char *b) {
    while (*a && *a==*b) {a++;b++;} return *a==*b;
}
static const char *find(const char *text,const char *part) {
    for (;*text;text++) {const char *a=text,*b=part;while (*b && *a==*b) {a++;b++;}if (!*b)return text;}return 0;
}
int sandbox_fs_test_rpc(const char *policy,int32_t operation,void *pointer,int32_t *error) {
    uint64_t *args=pointer;
    int control=LINUX_SYSCALL(__NR_openat,LINUX_AT_FDCWD,"/workspace/runtime/sandbox-fs-query-enable",0,0);
    char enabled=0;
    if (control>=0) {LINUX_SYSCALL(__NR_read,control,&enabled,1);LINUX_SYSCALL(__NR_close,control);}
    if (enabled!='1' || !equal(policy,"Sandbox") || operation!=2 || args[3]!=1 ||
        !find((const char *)(uintptr_t)args[4],"/linuxcode-sandbox-fs-"))
        return dserver_rpc_mac_syscall(policy,operation,pointer,error);
    const char *path=(const char *)(uintptr_t)args[4],*op=(const char *)(uintptr_t)args[2];
    int result=0;*error=0;uint64_t *decision=(uint64_t *)(uintptr_t)args[0];*decision=0;
    if (args[5]!=2 || args[1]) *error=EINVAL;
    else if (find(path,"transport-error")) result=-11; /* Linux EAGAIN -> Darwin EAGAIN */
    else if (find(path,"query-error")) *error=EIO;
    else if ((equal(op,"file-write-create") && find(path,"deny-create")) ||
             (equal(op,"file-write-unlink") && find(path,"deny-unlink"))) *decision=1;
    else {
        if (find(path,"/parentA/swap-parent")) {
            struct vchroot_expand_args old={.flags=0,.dfd=LINUX_AT_FDCWD};
            struct vchroot_expand_args saved={.flags=0,.dfd=LINUX_AT_FDCWD};
            const char *suffix=find(path,"/parentA/swap-parent");size_t length=suffix-path;
            for (size_t i=0;i<length;i++) old.path[i]=saved.path[i]=path[i];
            const char *a="/parentA",*b="/savedA";
            for (size_t i=0;;i++) {old.path[length+i]=a[i];if (!a[i])break;}
            for (size_t i=0;;i++) {saved.path[length+i]=b[i];if (!b[i])break;}
            int status=vchroot_expand(&old);if (!status)status=vchroot_expand(&saved);
            if (!status)status=LINUX_SYSCALL(__NR_renameat,old.dfd,old.path,saved.dfd,saved.path);
            if (!status)status=LINUX_SYSCALL(__NR_symlinkat,"parentB",old.dfd,old.path);
            if (status) *error=EIO;
        }
        if (!*error) result=dserver_rpc_mac_syscall(policy,operation,pointer,error);
    }
    char line[4608];int n=__simple_snprintf(line,sizeof line,"FS_QUERY operation=%s path=%s transport=%d error=%d decision=%llu\n",op,path,result,*error,(unsigned long long)*decision);
    int log=LINUX_SYSCALL(__NR_openat,LINUX_AT_FDCWD,"/workspace/logs/sandbox-fs-capture-events.log",0x441,0600);
    if (log>=0) {if (n>0 && n<sizeof line)LINUX_SYSCALL(__NR_write,log,line,n);LINUX_SYSCALL(__NR_close,log);}
    return result;
}
