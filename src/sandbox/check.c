/* Intel Sandbox query ABI, checked against the original native implementation.
 * The policy supplies the decision. An absent policy remains a real error.
 */
#include "sandbox.h"
#include <stdarg.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

extern int __mac_syscall(const char *, int, void *);

const enum sandbox_filter_type SANDBOX_CHECK_NO_REPORT = 0x40000000;
const enum sandbox_filter_type SANDBOX_CHECK_CANONICAL = 0x20000000;
const enum sandbox_filter_type SANDBOX_CHECK_NOFOLLOW = 0x10000000;
const enum sandbox_filter_type SANDBOX_CHECK_NO_APPROVAL = 0;
const enum sandbox_filter_type SANDBOX_CHECK_ALLOW_APPROVAL = 0x08000000;
const enum sandbox_filter_type SANDBOX_CHECK_POSIX_READABLE = 0x04000000;
const enum sandbox_filter_type SANDBOX_CHECK_POSIX_WRITEABLE = 0x02000000;

static int check_common(uint64_t pid, uint64_t version, uint64_t identity_flags,
                        const char *operation, uint32_t filter, va_list values)
{
    static const uint16_t selectors[20] = {0,1,6,7,25,27,28,33,34,35,240,241,50,19,65,45,75,5,52,69};
    uint64_t result=0, args[20]={0}, pair[2]={0};
    if (operation && !strcmp(operation,"iokit-open")) {
        fprintf(stderr,"sandbox operation \"%s\" is obsolete; replace with \"%s\"\n",operation,"iokit-open-user-client");
        operation="iokit-open-user-client";
    }
    args[0]=(uintptr_t)&result;args[1]=pid;args[2]=(uintptr_t)operation;
    args[5]=identity_flags;args[6]=version;
    static const uint8_t policy_bits[6]={1,2,8,16,32,64};
    for (unsigned i=0;i<6;i++) if (filter & (1u<<(30-i))) args[5]|=policy_bits[i];
    unsigned kind=filter & 0x81ffffffu;
    if (kind>=20) {errno=EINVAL;return -1;}
    args[3]=selectors[kind];
    switch (kind) {
        case 0:break;
        case 10:case 14:case 16:case 18:
            args[4]=(uint32_t)va_arg(values,int);break;
        case 9:
            pair[0]=(uintptr_t)va_arg(values,const void *);
            pair[1]=(uint64_t)(int64_t)va_arg(values,int);
            args[4]=(uintptr_t)pair;break;
        case 11: {
            const uint32_t *first=va_arg(values,const uint32_t *);
            const uint64_t *second=va_arg(values,const uint64_t *);
            pair[0]=*second;pair[1]=*first;args[4]=(uintptr_t)pair;break;
        }
        default:args[4]=(uintptr_t)va_arg(values,const void *);break;
    }
    int status=__mac_syscall("Sandbox",2,args);
    int saved_errno=errno;
    if (getenv("DARLING_SANDBOX_TRACE")) {
        static unsigned count;
        if (__atomic_fetch_add(&count,1,__ATOMIC_RELAXED)<128)
            fprintf(stderr,"DARLING_SANDBOX_QUERY pid=%llu version=%llu operation=%s filter=%#x policy_flags=%#llx status=%d decision=%llu errno=%d\n",
                (unsigned long long)pid,(unsigned long long)version,operation?operation:"<null>",filter,
                (unsigned long long)args[5],status,(unsigned long long)result,saved_errno);
    }
    errno=saved_errno;
    return status ? -1 : result!=0;
}

int sandbox_check(pid_t pid, const char *operation, enum sandbox_filter_type filter, ...)
{
    va_list values;va_start(values,filter);
    int result=check_common((uint64_t)(int64_t)pid,0,0,operation,(uint32_t)filter,values);
    va_end(values);return result;
}

int sandbox_check_by_audit_token(audit_token_t token, const char *operation, enum sandbox_filter_type filter, ...)
{
    va_list values;va_start(values,filter);
    int result=check_common(token.val[5],token.val[7],0x40000000,operation,(uint32_t)filter,values);
    va_end(values);return result;
}
