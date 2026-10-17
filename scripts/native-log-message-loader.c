/* Defer loading the original Intel formatter until libSystem is initialized.
 * All message bytes and the owned return value pass through unchanged. */
#include <pthread.h>
#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static pthread_once_t once=PTHREAD_ONCE_INIT;
static char *(*original_copy)(const void *);
static void load_formatter(void) {
    void *handle=dlopen("/usr/lib/libDarlingMetrics.dylib",RTLD_LAZY|RTLD_LOCAL);
    if(!handle){fprintf(stderr,"Original log formatter dlopen: %s\n",dlerror());abort();}
    original_copy=(char *(*)(const void *))dlsym(handle,"os_log_copy_message_string");
    Dl_info owner;
    if(!original_copy||!dladdr((void *)original_copy,&owner)||!owner.dli_fname||
        strcmp(owner.dli_fname,"/usr/lib/libDarlingMetrics.dylib")) {
        fputs("Original log formatter has an unexpected owner\n",stderr);abort();
    }
}
char *os_log_copy_message_string(const void *message) {
    int saved=errno;pthread_once(&once,load_formatter);errno=saved;
    return original_copy(message);
}
