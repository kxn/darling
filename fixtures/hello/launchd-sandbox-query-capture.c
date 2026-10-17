/* Test-only query transport. Only named test services receive injected results;
 * all other queries continue through the real MAC syscall and server. */
#include <stdint.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
extern int __mac_syscall(const char *, int, void *);
int darling_test_mac_syscall(const char *policy, int operation, void *arguments) {
    if (strcmp(policy,"Sandbox") || operation!=2) return __mac_syscall(policy,operation,arguments);
    uint64_t *args=arguments;
    if (!args[2] || (args[3]!=6 && args[3]!=7)) return __mac_syscall(policy,operation,arguments);
    const char *name=(const char *)(uintptr_t)args[4], *op=(const char *)(uintptr_t)args[2];
    const char prefix[]="org.linuxcode.sandbox-test.";
    if (strncmp(name,prefix,sizeof prefix-1)) return __mac_syscall(policy,operation,arguments);
    int status;
    if (!(args[5]&0x40000000) || !args[6] || !args[1] || args[1]==(unsigned)getpid()) {
        errno=EINVAL; status=-1;
    } else if ((!strcmp(op,"mach-register") && strstr(name,".error-reg.")) ||
               (!strcmp(op,"mach-lookup") && strstr(name,".error-lookup."))) {
        errno=EIO; status=-1;
    } else if ((!strcmp(op,"mach-register") && strstr(name,".deny-reg.")) ||
               (!strcmp(op,"mach-lookup") && strstr(name,".deny-lookup."))) {
        *(uint64_t *)(uintptr_t)args[0]=1; status=0;
    } else status=__mac_syscall(policy,operation,arguments);
    int saved=errno;
    char line[1024]; int length=snprintf(line,sizeof line,
        "QUERY pid=%llu version=%llu operation=%s selector=%llu name=%s status=%d decision=%llu errno=%d\n",
        (unsigned long long)args[1],(unsigned long long)args[6],op,(unsigned long long)args[3],name,status,
        (unsigned long long)*(uint64_t *)(uintptr_t)args[0],saved);
    int fd=open("/Volumes/SystemRoot/workspace/logs/launchd-sandbox-capture-events.log",O_WRONLY|O_CREAT|O_APPEND,0600);
    if (fd>=0) { if (length>0 && (size_t)length<sizeof line) write(fd,line,length); close(fd); }
    errno=saved; return status;
}
