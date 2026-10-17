#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(c) do{if(!(c)){fprintf(stderr,"PERSONA_FAIL %d %s\n",__LINE__,#c);exit(1);}}while(0)
int main(void){setbuf(stdout,NULL);void *native=dlopen("/Volumes/SystemRoot/workspace/runtime/foundation-native-library-stage/libsystem_containermanager.dylib",RTLD_LAZY|RTLD_LOCAL);CHECK(native);
 void *(*create)(void)=dlsym(RTLD_DEFAULT,"container_query_create");void (*dispose)(void *)=dlsym(RTLD_DEFAULT,"container_query_free");void (*set)(void *,const char *)=dlsym(RTLD_DEFAULT,"container_query_set_persona_unique_string");void *(*error)(void *)=dlsym(RTLD_DEFAULT,"container_query_get_last_error");CHECK(create&&dispose&&set&&error);
 const char *names[]={"CONTAINER_PERSONA_PRIMARY","CONTAINER_PERSONA_CURRENT"};
 for(unsigned i=0;i<2;i++){
  const char *const *value=dlsym(RTLD_DEFAULT,names[i]);const char *const *original=dlsym(native,names[i]);Dl_info image;CHECK(value&&original&&*value&&*original&&!strcmp(*value,*original));CHECK(value!=original&&*value!=*original);CHECK(dladdr(value,&image)&&strstr(image.dli_fname,"libDarlingContainerPersona.dylib"));
  void *q=create();CHECK(q&&!error(q));set(q,*value);CHECK(!error(q));
  // The pinned native setter duplicates its C-string argument into query+0x38.
  // Check the actual owned value; no protected daemon query is performed.
  const char *stored=NULL;memcpy(&stored,(char *)q+0x38,sizeof(stored));CHECK(stored&&stored!=*value&&!strcmp(stored,*original));dispose(q);
  printf("NATIVE_CONTAINER_PERSONA_OWNED_QUERY_STRING_OK %s %s\n",names[i],*value);
 }
 puts("CONTAINER_PERSONA_POINTER_VARIABLE_ABI_ORIGINAL_VALUES_AND_REAL_SETTER_OK");return 0;
}
