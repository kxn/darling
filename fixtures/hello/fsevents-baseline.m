#import <Foundation/Foundation.h>
#include <CoreServices/CoreServices.h>
#include <dispatch/dispatch.h>
#include <dlfcn.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do{if(!(x)){fprintf(stderr,"FSEVENTS_BASELINE_FAIL line=%d %s\n",__LINE__,#x);abort();}}while(0)
static NSMutableSet *received;static dispatch_semaphore_t ready;
static void callback(ConstFSEventStreamRef stream,void *info,size_t count,void *paths,const FSEventStreamEventFlags flags[],const FSEventStreamEventId ids[]){@autoreleasepool{for(size_t i=0;i<count;i++){NSString *path=(NSString *)CFArrayGetValueAtIndex((CFArrayRef)paths,i);[received addObject:[path lastPathComponent]];}if(count)dispatch_semaphore_signal(ready);}}
int main(int argc,char **argv){setbuf(stdout,NULL);@autoreleasepool{
 char directory[]="/tmp/fsevents-baseline.XXXXXX";CHECK(mkdtemp(directory));NSString *path=[NSString stringWithUTF8String:directory];received=[[NSMutableSet alloc]init];ready=dispatch_semaphore_create(0);dispatch_queue_t queue=dispatch_queue_create("fsevents.baseline.delivery",NULL);dispatch_suspend(queue);
 NSArray *paths=@[path];FSEventStreamContext context={0};FSEventStreamRef stream=FSEventStreamCreate(NULL,callback,&context,(CFArrayRef)paths,kFSEventStreamEventIdSinceNow,60.0,kFSEventStreamCreateFlagUseCFTypes|kFSEventStreamCreateFlagFileEvents);CHECK(stream);FSEventStreamSetDispatchQueue(stream,queue);CHECK(FSEventStreamStart(stream));
 Dl_info owner;CHECK(dladdr((void*)FSEventStreamCreate,&owner));printf("FSEVENTS_BASELINE_PROVIDER %s\n",owner.dli_fname);if(argc>1)CHECK(strstr(owner.dli_fname,"/runtime/fsevents-source/frameworks/"));
 puts("FSEVENTS_BASELINE_REAL_WATCH_STARTED");
 for(unsigned i=0;i<64;i++){char file[1024];snprintf(file,sizeof(file),"%s/file-%u",directory,i);int fd=open(file,O_CREAT|O_WRONLY|O_EXCL,0600);CHECK(fd>=0);CHECK(write(fd,"x",1)==1);CHECK(!close(fd));}
 dispatch_resume(queue);long waited=dispatch_semaphore_wait(ready,dispatch_time(DISPATCH_TIME_NOW,3*NSEC_PER_SEC));dispatch_sync(queue,^{});unsigned observed=(unsigned)[received count];FSEventStreamEventId latest=FSEventStreamGetLatestEventId(stream);
 printf("FSEVENTS_BASELINE_REAL_BURST expected=64 unique_paths=%u waited=%ld latest=%llu\n",observed,waited,(unsigned long long)latest);
 printf("FSEVENTS_BASELINE_FLUSH_ASYNC_PRESENT %d\n",dlsym(RTLD_DEFAULT,"FSEventStreamFlushAsync")!=NULL);
 FSEventStreamStop(stream);FSEventStreamInvalidate(stream);FSEventStreamRelease(stream);dispatch_sync(queue,^{});dispatch_release(queue);dispatch_release(ready);[received release];
 for(unsigned i=0;i<64;i++){char file[1024];snprintf(file,sizeof(file),"%s/file-%u",directory,i);unlink(file);}rmdir(directory);
 return waited==0&&observed==64?0:1;
}}
