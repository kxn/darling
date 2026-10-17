#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <dlfcn.h>
#include <pthread.h>
#define CHECK(c) do { if(!(c)){fprintf(stderr,"RUNNABLE_ARCHS_FAIL line=%d %s\n",__LINE__,#c);abort();}}while(0)
extern void source_for_each_runnable_arch_name(void (^)(const char *,bool *));
extern void reference_for_each_runnable_arch_name(void (^)(const char *,bool *));
static char directory[1024];
static const char prefix[]="/System/Cryptexes/OS/System/Library/dyld/";
static const char *caches[]={"dyld_shared_cache_arm64e","dyld_shared_cache_x86_64h","dyld_shared_cache_x86_64"};
static __thread char probes[4096];
int runnable_fixture_stat(const char *path,struct stat *st) {
 CHECK(!strncmp(path,prefix,sizeof(prefix)-1));
 const char *name=path+sizeof(prefix)-1;char local[1200];
 CHECK(snprintf(local,sizeof(local),"%s/%s",directory,name)<sizeof(local));
 CHECK(strlen(probes)+strlen(name)+2<sizeof(probes));strlcat(probes,name,sizeof(probes));strlcat(probes,";",sizeof(probes));
 return stat(local,st);
}
struct outcome {char names[128];char trace[4096];unsigned count;};
static struct outcome collect(void (*enumerate)(void (^)(const char*,bool*)),unsigned stop_at) {
 __block struct outcome result={0};__block bool *stop_address=NULL;probes[0]=0;
 enumerate(^(const char *name,bool *stop){
  CHECK(name&&stop&&!*stop);if(stop_address)CHECK(stop_address==stop);stop_address=stop;
  CHECK(strlen(result.names)+strlen(name)+2<sizeof(result.names));strlcat(result.names,name,sizeof(result.names));strlcat(result.names,";",sizeof(result.names));
  result.count++;if(result.count==stop_at)*stop=true;
 });
 strlcpy(result.trace,probes,sizeof(result.trace));return result;
}
static void setup(unsigned state,bool dirs) {
 for(unsigned i=0;i<3;i++) {
  char path[1200];snprintf(path,sizeof(path),"%s/%s",directory,caches[i]);unlink(path);rmdir(path);strlcat(path,".development",sizeof(path));unlink(path);rmdir(path);
  unsigned kind=state%3;state/=3;if(!kind)continue;
  snprintf(path,sizeof(path),"%s/%s%s",directory,caches[i],kind==2?".development":"");
  if(dirs)CHECK(!mkdir(path,0700));else{int fd=open(path,O_WRONLY|O_CREAT|O_EXCL,0600);CHECK(fd>=0);CHECK(!close(fd));}
 }
}
static unsigned compare(unsigned stop) {
 struct outcome actual=collect(source_for_each_runnable_arch_name,stop),expected=collect(reference_for_each_runnable_arch_name,stop);
 CHECK(actual.count==expected.count);CHECK(!strcmp(actual.names,expected.names));CHECK(!strcmp(actual.trace,expected.trace));
 return 1;
}
static void *worker(void *unused){for(unsigned i=0;i<64;i++)compare(i%4);return NULL;}
int main(void) {
 setbuf(stdout,NULL);strlcpy(directory,"/tmp/runnable-archs.XXXXXX",sizeof(directory));CHECK(mkdtemp(directory));unsigned cases=0;
 for(unsigned dirs=0;dirs<2;dirs++)for(unsigned state=0;state<27;state++){setup(state,dirs);for(unsigned stop=0;stop<5;stop++)cases+=compare(stop);}
 // stat follows symlinks; a dangling main name must still try .development.
 setup(0,false);char target[1200],link[1200];snprintf(target,sizeof(target),"%s/target",directory);CHECK(!mkdir(target,0700));snprintf(link,sizeof(link),"%s/%s",directory,caches[1]);CHECK(!symlink(target,link));for(unsigned stop=0;stop<3;stop++)cases+=compare(stop);
 CHECK(!rmdir(target));snprintf(link,sizeof(link),"%s/%s.development",directory,caches[1]);int fd=open(link,O_WRONLY|O_CREAT,0600);CHECK(fd>=0);CHECK(!close(fd));for(unsigned stop=0;stop<3;stop++)cases+=compare(stop);
 setup(0,false);pthread_t threads[8];for(unsigned i=0;i<8;i++)CHECK(!pthread_create(&threads[i],NULL,worker,NULL));for(unsigned i=0;i<8;i++)CHECK(!pthread_join(threads[i],NULL));cases+=512;CHECK(!rmdir(directory));
 puts("ORIGINAL_RUNNABLE_ARCHS_CACHE_FILES_DEVELOPMENT_DIRECTORIES_SYMLINK_STOP_ORDER_AND_CONCURRENCY_OK");printf("RUNNABLE_ARCHS_DIFFERENTIAL_CASES %u\n",cases);
 // This call resolves through libSystem to the actual rebuilt libdyld, not the
 // locally renamed test object or the relocated native oracle.
 void (*production)(void (^)(const char*,bool*))=dlsym(RTLD_DEFAULT,"macho_for_each_runnable_arch_name");Dl_info owner;CHECK(production&&dladdr(production,&owner));CHECK(strstr(owner.dli_fname,"/libdyld.dylib"));
 __block unsigned count=0;production(^(const char *name,bool *stop){CHECK(!strcmp(name,"x86_64"));CHECK(!*stop);count++;});CHECK(count==1);
 printf("SOURCE_RUNNABLE_ARCHS_REAL_LIBDYLD_OWNER_AND_GUEST_NO_CACHE_FALLBACK_OK %s\n",owner.dli_fname);return 0;
}
