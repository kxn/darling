#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <errno.h>
#include <dlfcn.h>
#include <string.h>
struct compiled_profile {const char *builtin;const void *data;uint64_t length;};
int main(void){
 setbuf(stdout,NULL);
 void *lib=dlopen("/usr/lib/libsandbox.1.dylib",RTLD_LAZY|RTLD_LOCAL);if(!lib){printf("POLICY_DUMP_LOAD_ERROR %s\n",dlerror());return 1;}
 void *(*create)(void)=dlsym(lib,"sandbox_create_params");int (*set)(void*,const char*,const char*)=dlsym(lib,"sandbox_set_param");void (*destroy)(void*)=dlsym(lib,"sandbox_free_params");struct compiled_profile *(*compile)(const char*,void*,char**)=dlsym(lib,"sandbox_compile_string");struct compiled_profile *(*named)(const char*,void*,char**)=dlsym(lib,"sandbox_compile_named");void (*release)(void*)=dlsym(lib,"sandbox_free_profile");
 if(!create||!set||!destroy||!compile||!named||!release)return 2;
 void *params=create();if(!params)return 3;
 if(set(params,"DARLING_TEST_ROOT","/tmp/darling-sandbox-policy")||set(params,"DARWIN_USER_TEMP_DIR","/tmp/com.apple.coreservicesd")||set(params,"DARWIN_USER_CACHE_DIR","/root/.cache/com.apple.coreservicesd"))return 4;
 const char *names[]={"allow-all","deny-all","subpath-read","literal-read","regex-read","mach-service","process-self","write-temp","coreservicesd"};
 const char *inputs[]={"(version 1)(allow default)","(version 1)(deny default)","(version 1)(deny default)(allow file-read* (subpath (param \"DARLING_TEST_ROOT\")))","(version 1)(deny default)(allow file-read-data (literal \"/tmp/darling-sandbox-policy/file\"))","(version 1)(deny default)(allow file-read-data (regex #\"^/tmp/darling-policy/.*$\"))","(version 1)(deny default)(allow mach-lookup (global-name \"com.apple.DiskArbitration.diskarbitrationd\"))","(version 1)(deny default)(allow process-info* (target self))","(version 1)(allow default)(deny file-write*)(allow file-write* (subpath (param \"DARLING_TEST_ROOT\")))",NULL};
 for(unsigned i=0;i<9;i++){
  char *err=NULL;struct compiled_profile *profile=inputs[i]?compile(inputs[i],params,&err):named("com.apple.coreservicesd",params,&err);
  if(!profile){printf("POLICY_DUMP_COMPILE_ERROR %s %s\n",names[i],err?err:"nil");return 5;}
  printf("POLICY_DUMP %s builtin=%s buffer=%p length=%llu\n",names[i],profile->builtin?profile->builtin:"nil",profile->data,(unsigned long long)profile->length);
  if(profile->builtin||!profile->data||profile->length<16||profile->length>1024*1024)return 6;
  char path[1024];snprintf(path,sizeof path,"/Volumes/SystemRoot/workspace/runtime/sandbox-policy-dump/%s.bin",names[i]);FILE *f=fopen(path,"wb");if(!f)return 7;
  if(fwrite(profile->data,1,profile->length,f)!=profile->length||fclose(f))return 8;
  snprintf(path,sizeof path,"/Volumes/SystemRoot/workspace/runtime/sandbox-policy-dump/%s.sb",names[i]);f=fopen(path,"w");if(!f)return 9;fputs(inputs[i]?inputs[i]:"; Unchanged original com.apple.coreservicesd profile and imports\n",f);fclose(f);
  release(profile);if(err)free(err);
 }
 destroy(params);puts("POLICY_DUMP_RETURNED");return 0;
}
