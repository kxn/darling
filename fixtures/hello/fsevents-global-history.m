#import <Foundation/Foundation.h>
#include <CoreServices/CoreServices.h>
#include <dispatch/dispatch.h>
#include <dlfcn.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>

static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr,"FSEVENTS_HISTORY_FAIL line=%d %s errno=%d\n",__LINE__,#x,errno); abort(); } } while(0)
typedef struct {
    NSMutableArray* paths;
    NSMutableArray* flags;
    dispatch_semaphore_t done;
    unsigned history, gaps;
    BOOL historyEnded, runMain, afterBoundary, rawPaths;
} Context;
static void callback(ConstFSEventStreamRef stream,void* info,size_t count,void* paths,
                     const FSEventStreamEventFlags flags[],const FSEventStreamEventId ids[]) {
    @autoreleasepool {
        Context* c=info;
        for(size_t i=0;i<count;i++) {
            NSString* path=c->rawPaths ? [NSString stringWithUTF8String:((char**)paths)[i]] :
                (id)CFArrayGetValueAtIndex((CFArrayRef)paths,i);
            CHECK(path && ids[i]);
            [c->paths addObject:path];[c->flags addObject:@(flags[i])];
            if(flags[i]&kFSEventStreamEventFlagHistoryDone) {
                CHECK(flags[i]==kFSEventStreamEventFlagHistoryDone);
                c->history++;c->historyEnded=YES;
                if(c->runMain)CFRunLoopStop(CFRunLoopGetCurrent());
                dispatch_semaphore_signal(c->done);
            } else {
                if(c->historyEnded)c->afterBoundary=YES;
                if(flags[i]&kFSEventStreamEventFlagUserDropped) {
                    CHECK(flags[i]&kFSEventStreamEventFlagMustScanSubDirs);c->gaps++;
                }
            }
        }
    }
}
static void initContext(Context* c) {
    memset(c,0,sizeof(*c));c->paths=[[NSMutableArray alloc]init];c->flags=[[NSMutableArray alloc]init];c->done=dispatch_semaphore_create(0);
}
static void clear(Context* c) { [c->paths removeAllObjects];[c->flags removeAllObjects];c->gaps=0; }
static void clean(Context* c) { [c->paths release];[c->flags release];dispatch_release(c->done); }
static void writeAt(NSString* path) {
    int fd=open([path UTF8String],O_WRONLY|O_CREAT|O_TRUNC,0600);CHECK(fd>=0);
    CHECK(write(fd,"real-mutation",13)==13);CHECK(close(fd)==0);
}
static void directory(NSString* path) { CHECK([[NSFileManager defaultManager]createDirectoryAtPath:path withIntermediateDirectories:YES attributes:nil error:NULL]); }
static FSEventStreamRef make(Context* c,NSArray* roots,FSEventStreamEventId since,dispatch_queue_t queue) {
    FSEventStreamContext context={0,c,NULL,NULL,NULL};
    FSEventStreamRef stream=FSEventStreamCreate(NULL,callback,&context,(CFArrayRef)roots,since,0,
        c->rawPaths ? 0 : kFSEventStreamCreateFlagUseCFTypes|kFSEventStreamCreateFlagFileEvents);
    CHECK(stream);FSEventStreamSetDispatchQueue(stream,queue);CHECK(FSEventStreamStart(stream));return stream;
}
static void finish(FSEventStreamRef stream,dispatch_queue_t queue) {
    FSEventStreamFlushSync(stream);FSEventStreamStop(stream);FSEventStreamInvalidate(stream);FSEventStreamRelease(stream);
    if(queue)dispatch_sync(queue,^{});
}
static BOOL modified(Context* c,NSString* path) {
    for(NSUInteger i=0;i<[c->paths count];i++)
        if([c->paths[i] isEqualToString:path]&&([c->flags[i]unsignedIntValue]&kFSEventStreamEventFlagItemModified))return YES;
    return NO;
}
int main(int argc,char** argv) { setbuf(stdout,NULL);@autoreleasepool {
    BOOL baseline=argc>1&&!strcmp(argv[1],"baseline");
    Dl_info owner;CHECK(dladdr((void*)FSEventStreamCreate,&owner));
    if(!baseline)CHECK(strstr(owner.dli_fname,"/runtime/global-fsevents-source/frameworks/"));
    printf("FSEVENTS_HISTORY_PROVIDER %s\n",owner.dli_fname);
    char temp[]="/tmp/fsevents-history.XXXXXX";CHECK(mkdtemp(temp));
    NSString* root=[NSString stringWithUTF8String:temp];NSString* left=[root stringByAppendingPathComponent:@"left"];
    NSString* right=[root stringByAppendingPathComponent:@"right"];directory(left);directory(right);
    NSString* deep=[left stringByAppendingPathComponent:@"a/b/c/d/e/f"];directory(deep);
    CHECK(symlink("..",[[deep stringByAppendingPathComponent:@"cycle"]UTF8String])==0);
    dispatch_queue_t queue=dispatch_queue_create("history.actual.callbacks",DISPATCH_QUEUE_SERIAL);
    Context historical;initContext(&historical);
    FSEventStreamRef stream=make(&historical,@[left,right],123456,queue);
    if(baseline) {
        long missing=dispatch_semaphore_wait(historical.done,dispatch_time(DISPATCH_TIME_NOW,NSEC_PER_SEC/4));
        finish(stream,queue);clean(&historical);dispatch_release(queue);
        CHECK([[NSFileManager defaultManager]removeItemAtPath:root error:NULL]);
        puts(missing?"BASELINE_FINITE_SINCEWHEN_HAS_NO_HISTORY_COMPLETION":"BASELINE_HISTORY_COMPLETED");return missing?2:0;
    }
    CHECK(dispatch_semaphore_wait(historical.done,dispatch_time(DISPATCH_TIME_NOW,2*NSEC_PER_SEC))==0);
    FSEventStreamFlushSync(stream);CHECK(historical.gaps==2&&historical.history==1&&!historical.afterBoundary);
    CHECK([historical.paths count]==3);
    FSEventStreamStop(stream);CHECK(FSEventStreamStart(stream));FSEventStreamFlushSync(stream);CHECK(historical.history==1);
    finish(stream,queue);clean(&historical);
    puts("FSEVENTS_FINITE_HISTORY_GAPS_BEFORE_SINGLE_BOUNDARY_AND_RESTART_OK");

    Context current;initContext(&current);stream=make(&current,@[left],kFSEventStreamEventIdSinceNow,queue);
    FSEventStreamFlushSync(stream);CHECK(current.history==0&&[current.paths count]==0);
    NSString* leaf=[deep stringByAppendingPathComponent:@"existing-tree-file"];
    writeAt(leaf);FSEventStreamFlushSync(stream);CHECK(modified(&current,leaf));clear(&current);
    NSString* added=[deep stringByAppendingPathComponent:@"new/tree/inside"];directory(added);
    NSString* raced=[added stringByAppendingPathComponent:@"before-watch"];writeAt(raced);
    FSEventStreamFlushSync(stream);CHECK(current.gaps>0);clear(&current);
    NSString* addedLeaf=[added stringByAppendingPathComponent:@"after-watch"];writeAt(addedLeaf);
    FSEventStreamFlushSync(stream);CHECK(modified(&current,addedLeaf));clear(&current);
    puts("FSEVENTS_RECURSIVE_INITIAL_AND_NEW_SUBTREE_WITH_REAL_GAP_OK");

    NSString* moved=[left stringByAppendingPathComponent:@"renamed-tree"];
    CHECK(rename([[left stringByAppendingPathComponent:@"a"]UTF8String],[moved UTF8String])==0);
    FSEventStreamFlushSync(stream);
    unsigned renameFlags=0;for(NSNumber* value in current.flags)renameFlags|=[value unsignedIntValue];
    CHECK(renameFlags&kFSEventStreamEventFlagItemRenamed);
    CHECK([current.paths containsObject:moved]);clear(&current);
    NSString* movedLeaf=[moved stringByAppendingPathComponent:@"b/c/d/e/f/after-rename"];
    writeAt(movedLeaf);FSEventStreamFlushSync(stream);CHECK(modified(&current,movedLeaf));clear(&current);
    NSString* exported=[right stringByAppendingPathComponent:@"outside-watch"];
    CHECK(rename([moved UTF8String],[exported UTF8String])==0);FSEventStreamFlushSync(stream);clear(&current);
    writeAt([exported stringByAppendingPathComponent:@"b/c/d/e/f/outside"]);FSEventStreamFlushSync(stream);
    CHECK([current.paths count]==0);
    CHECK(symlink([exported UTF8String],[[left stringByAppendingPathComponent:@"external-link"]UTF8String])==0);
    FSEventStreamFlushSync(stream);clear(&current);
    writeAt([exported stringByAppendingPathComponent:@"b/c/d/e/f/outside-link"]);FSEventStreamFlushSync(stream);
    CHECK([current.paths count]==0);
    finish(stream,queue);clean(&current);
    puts("FSEVENTS_DIRECTORY_RENAME_PATH_REMAP_AND_MOVE_OUT_UNWATCH_OK");

    Context main;initContext(&main);main.runMain=YES;main.rawPaths=YES;
    stream=make(&main,@[right],0,dispatch_get_main_queue());
    // This is the actual clang-stat-cache control flow: the main-queue history
    // callback stops the CF run loop. A dropped interval must invalidate cache.
    CFRunLoopRun();CHECK(main.history==1&&main.gaps>=1);
    FSEventStreamStop(stream);FSEventStreamInvalidate(stream);FSEventStreamRelease(stream);clean(&main);
    puts("FSEVENTS_REAL_MAIN_QUEUE_CF_RUNLOOP_HISTORY_CONSUMER_TERMINATES_OK");
    Context invalid;initContext(&invalid);NSArray* absent=@[[root stringByAppendingPathComponent:@"missing"]];
    FSEventStreamContext ctx={0,&invalid,NULL,NULL,NULL};errno=0;
    CHECK(!FSEventStreamCreate(NULL,callback,&ctx,(CFArrayRef)absent,kFSEventStreamEventIdSinceNow,0,0));CHECK(errno==ENOENT);clean(&invalid);
    dispatch_release(queue);CHECK([[NSFileManager defaultManager]removeItemAtPath:root error:NULL]);
    printf("FSEVENTS_RECURSIVE_HISTORY_CHECKS_OK checks=%u global_ids_implemented=1 durable_history_implemented=0\n",checks);
    return 0;
} }
