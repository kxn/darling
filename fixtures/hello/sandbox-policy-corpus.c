#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <dlfcn.h>
struct compiled_profile {const char *builtin;const void *data;uint64_t length;};
struct input {const char *name,*source;int named;};
#include "sandbox-policy-corpus.inc"
int main(int argc,char **argv){
 if(argc!=2)return 10;setbuf(stdout,NULL);
 void *lib=dlopen("/usr/lib/libsandbox.1.dylib",RTLD_LAZY|RTLD_LOCAL);if(!lib){printf("POLICY_CORPUS_LOAD_ERROR %s\n",dlerror());return 1;}
 void *(*create)(void)=dlsym(lib,"sandbox_create_params");int (*set)(void*,const char*,const char*)=dlsym(lib,"sandbox_set_param");void (*destroy)(void*)=dlsym(lib,"sandbox_free_params");struct compiled_profile *(*compile)(const char*,void*,char**)=dlsym(lib,"sandbox_compile_string");struct compiled_profile *(*named)(const char*,void*,char**)=dlsym(lib,"sandbox_compile_named");void (*release)(void*)=dlsym(lib,"sandbox_free_profile");
 if(!create||!set||!destroy||!compile||!named||!release)return 2;
 void *params=create();if(!params)return 3;
 if(set(params,"DARLING_TEST_ROOT","/tmp/darling-sandbox-policy")||set(params,"DARWIN_USER_TEMP_DIR","/tmp/com.apple.coreservicesd")||set(params,"DARWIN_USER_CACHE_DIR","/root/.cache/com.apple.coreservicesd"))return 4;
 for(unsigned i=0;i<sizeof inputs/sizeof inputs[0];i++){
  char *err=NULL;struct compiled_profile *p=inputs[i].named?named(inputs[i].source,params,&err):compile(inputs[i].source,params,&err);
  if(!p){printf("POLICY_CORPUS_COMPILE_ERROR %s %s\n",inputs[i].name,err?err:"nil");return 5;}
  if(p->builtin||!p->data||p->length<16||p->length>1024*1024)return 6;
  char path[1024];snprintf(path,sizeof path,"%s/%s.bin",argv[1],inputs[i].name);FILE *f=fopen(path,"wb");if(!f)return 7;
  if(fwrite(p->data,1,p->length,f)!=p->length||fclose(f))return 8;
  printf("POLICY_CORPUS_COMPILED %s %llu\n",inputs[i].name,(unsigned long long)p->length);release(p);if(err)free(err);
 }
 destroy(params);puts("POLICY_CORPUS_RETURNED");return 0;
}
