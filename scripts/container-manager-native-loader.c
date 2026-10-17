/* Defer provider loading until libSystem/libc++ initializers have completed. */
#include <dlfcn.h>
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static const char *names[]={
 "container_copy_from_path","container_copy_sandbox_token","container_create_or_lookup_app_group_paths_from_entitlements_4ls","container_create_or_lookup_path_for_platform","container_entitlements_copy_container_identifiers","container_error_copy_unlocalized_description","container_free_object","container_get_error_description","container_get_path","container_query_create","container_query_free","container_query_get_last_error","container_query_get_single_result","container_query_operation_set_flags","container_query_set_class","container_query_set_identifiers","container_query_set_persona_unique_string"};
static void *targets[sizeof(names)/sizeof(names[0])];
static pthread_once_t once=PTHREAD_ONCE_INIT;
static void load(void){
 const char *path="/Volumes/SystemRoot/workspace/runtime/foundation-native-library-stage/libsystem_containermanager.dylib";
 void *handle=dlopen(path,RTLD_LAZY|RTLD_LOCAL);
 for(unsigned i=0;i<sizeof(names)/sizeof(names[0]);i++){
  targets[i]=handle?dlsym(handle,names[i]):NULL;Dl_info owner;
  if(!targets[i]||!dladdr(targets[i],&owner)||strcmp(owner.dli_fname,path)){
   fprintf(stderr,"Darling: original ContainerManager entry unavailable or wrong owner: %s\n",names[i]);abort();
  }
 }
}
/* Also exposed by this helper for provenance tests; libSystem reexports only
 * the original 17 API names, never this diagnostic entry. */
void *linuxcode_container_manager_original_address(unsigned index){
 int saved=errno;
 if(index>=sizeof(names)/sizeof(names[0]))abort();
 pthread_once(&once,load);errno=saved;return targets[index];
}
