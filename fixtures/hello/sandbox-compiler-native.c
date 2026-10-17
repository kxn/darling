#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <dlfcn.h>
#include <string.h>
int main(void){
 setbuf(stdout,NULL);setenv("STUB_VERBOSE","1",1);
 void *lib=dlopen("/usr/lib/libsandbox.1.dylib",RTLD_LAZY|RTLD_LOCAL);if(!lib){printf("SANDBOX_COMPILER_DLOPEN_FAILED %s\n",dlerror());return 1;}
 void *(*create)(void)=dlsym(lib,"sandbox_create_params");int (*set)(void*,const char*,const char*)=dlsym(lib,"sandbox_set_param");void (*destroy)(void*)=dlsym(lib,"sandbox_free_params");void *(*compile)(const char*,void*,char**)=dlsym(lib,"sandbox_compile_string");void (*release)(void*)=dlsym(lib,"sandbox_free_profile");
 if(!create||!set||!destroy||!compile||!release){puts("SANDBOX_COMPILER_SYMBOL_MISSING");return 1;}
 Dl_info owner={0};dladdr(create,&owner);printf("SANDBOX_COMPILER_OWNER %s\n",owner.dli_fname);
 errno=EDOM;void *params=create();printf("SANDBOX_COMPILER_PARAMS ptr=%p errno=%d\n",params,errno);if(!params)return 2;
 int st=set(params,"DARLING_TEST_ROOT","/tmp/darling-sandbox-compiler");printf("SANDBOX_COMPILER_SET_PARAM status=%d errno=%d\n",st,errno);if(st)return 3;
 const char *inputs[]={"(version 1)(allow default)","(version 1)(deny default)(allow file-read* (subpath (param \"DARLING_TEST_ROOT\")))","(version 1)(allow not-a-real-sandbox-operation)","(version 1)(allow default"};
 for(unsigned i=0;i<4;i++){char *err=NULL;errno=0;void *profile=compile(inputs[i],params,&err);printf("SANDBOX_COMPILER_RESULT index=%u ptr=%p errno=%d error=%s\n",i,profile,errno,err?err:"nil");if(profile)release(profile);if(err)free(err);}
 destroy(params);puts("SANDBOX_COMPILER_PROBE_RETURNED");return 0;
}
