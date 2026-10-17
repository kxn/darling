#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
int combine_native_owner(void){
 const char *name="$s7Combine4JustV14setFailureType2tos6ResultOAAE9PublisherVyxqd___Gqd__m_ts5ErrorRd__lF";
 void *fn=dlsym(RTLD_DEFAULT,name);Dl_info owner;
 if(!fn||!dladdr(fn,&owner)||!strstr(owner.dli_fname,"/runtime/combine-native/frameworks/Combine.framework/")){fprintf(stderr,"COMBINE_NATIVE_WRONG_OWNER %s\n",fn?owner.dli_fname:"<nil>");return 0;}
 printf("COMBINE_NATIVE_ORIGINAL_SET_FAILURE_TYPE_OWNER_OK %s\n",owner.dli_fname);fflush(stdout);return 1;
}
