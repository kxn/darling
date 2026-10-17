#include <dlfcn.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <xpc/xpc.h>
#define CHECK(c) do {if(!(c)){fprintf(stderr,"CONTAINER_API_FAIL %d %s\n",__LINE__,#c);exit(1);}}while(0)
int main(int argc,char **argv){setbuf(stdout,NULL);CHECK(argc==4);
 void *system=dlopen(argv[1],RTLD_LAZY|RTLD_LOCAL),*native=dlopen(argv[2],RTLD_LAZY|RTLD_LOCAL);CHECK(system&&native);
 const char *names[]={"container_copy_from_path","container_copy_sandbox_token","container_create_or_lookup_app_group_paths_from_entitlements_4ls","container_create_or_lookup_path_for_platform","container_entitlements_copy_container_identifiers","container_error_copy_unlocalized_description","container_free_object","container_get_error_description","container_get_path","container_query_create","container_query_free","container_query_get_last_error","container_query_get_single_result","container_query_operation_set_flags","container_query_set_class","container_query_set_identifiers","container_query_set_persona_unique_string"};
 for(unsigned i=0;i<sizeof(names)/sizeof(names[0]);i++){
  void *a=dlsym(system,names[i]),*b=dlsym(native,names[i]);Dl_info owner;CHECK(a&&b&&a!=b&&dladdr(a,&owner));CHECK(!strcmp(owner.dli_fname,argv[3]));
  void *helper=dlopen(argv[3],RTLD_LAZY|RTLD_LOCAL);CHECK(helper);
  void *(*original)(unsigned)=dlsym(helper,"linuxcode_container_manager_original_address");CHECK(original&&original(i)==b);CHECK(dladdr(b,&owner)&&!strcmp(owner.dli_fname,argv[2]));dlclose(helper);
 }
 printf("CONTAINER_API_ORIGINAL_PROVIDER_17_POINTERS_OK\n");
 void *(*create)(void)=dlsym(system,"container_query_create");
 void (*dispose)(void*)=dlsym(system,"container_query_free");
 void *(*last_error)(void*)=dlsym(system,"container_query_get_last_error");
 void (*set_class)(void*,uint64_t)=dlsym(system,"container_query_set_class");
 void (*set_flags)(void*,uint64_t)=dlsym(system,"container_query_operation_set_flags");
 void (*set_ids)(void*,xpc_object_t)=dlsym(system,"container_query_set_identifiers");
 for(unsigned i=0;i<128;i++){
  void *q=create(),*other=create();CHECK(q&&other&&q!=other);CHECK(last_error(q)==NULL&&last_error(other)==NULL);
  set_class(q,1+i%14);set_flags(q,0);
  xpc_object_t identifier=xpc_string_create("org.linuxcode.container-query-fixture");CHECK(identifier);set_ids(q,identifier);xpc_release(identifier);CHECK(last_error(q)==NULL);
  dispose(q);CHECK(last_error(other)==NULL);dispose(other);
 }
 printf("CONTAINER_API_REAL_QUERY_LOCAL_LIFETIME_256_OBJECTS_OK\n");
 // No get_single_result call is replaced or short-circuited here. A real
 // container daemon and positive records still require a separate test.
 return 0;
}
