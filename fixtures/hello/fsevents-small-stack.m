#import <Foundation/Foundation.h>
#include <CoreServices/CoreServices.h>
#include <dispatch/dispatch.h>
#include <pthread.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(c) do{if(!(c)){fprintf(stderr,"SMALL_STACK_FSEVENTS_FAIL %d %s\n",__LINE__,#c);abort();}}while(0)
static unsigned received;
static void callback(ConstFSEventStreamRef stream,void *info,size_t count,void *paths,const FSEventStreamEventFlags *flags,const FSEventStreamEventId *ids){
    for(size_t i=0;i<count;i++){
        NSString *path=[(NSArray*)paths objectAtIndex:i];
        CHECK([path hasSuffix:@"/actual-file"]);CHECK(ids[i]>0);
        __sync_fetch_and_add(&received,1);
    }
}
static void *worker(void *ignored){@autoreleasepool{
    size_t size=pthread_get_stacksize_np(pthread_self());CHECK(size==64*1024);
    char path[]="/tmp/fsevents-small-stack.XXXXXX";CHECK(mkdtemp(path));
    NSArray *paths=@[[NSString stringWithUTF8String:path]];
    FSEventStreamRef stream=FSEventStreamCreate(NULL,callback,NULL,(CFArrayRef)paths,kFSEventStreamEventIdSinceNow,60,kFSEventStreamCreateFlagUseCFTypes|kFSEventStreamCreateFlagFileEvents);CHECK(stream);
    dispatch_queue_t queue=dispatch_queue_create("actual.small.stack.events",DISPATCH_QUEUE_SERIAL);
    FSEventStreamSetDispatchQueue(stream,queue);CHECK(FSEventStreamStart(stream));
    char file[512];snprintf(file,sizeof(file),"%s/actual-file",path);
    int fd=open(file,O_CREAT|O_WRONLY|O_TRUNC,0600);CHECK(fd>=0);CHECK(write(fd,"x",1)==1);CHECK(close(fd)==0);
    FSEventStreamFlushSync(stream);CHECK(received==2);
    FSEventStreamStop(stream);FSEventStreamInvalidate(stream);FSEventStreamRelease(stream);
    dispatch_sync(queue,^{});dispatch_release(queue);CHECK(unlink(file)==0);CHECK(rmdir(path)==0);
    printf("SOURCE_FSEVENTS_REAL_START_AND_SYNC_FLUSH_ON_64K_STACK_OK events=%u stack=%zu\n",received,size);
    return NULL;
}}
int main(void){setbuf(stdout,NULL);pthread_attr_t attr;CHECK(pthread_attr_init(&attr)==0);CHECK(pthread_attr_setstacksize(&attr,64*1024)==0);pthread_t thread;CHECK(pthread_create(&thread,&attr,worker,NULL)==0);CHECK(pthread_attr_destroy(&attr)==0);CHECK(pthread_join(thread,NULL)==0);return 0;}
