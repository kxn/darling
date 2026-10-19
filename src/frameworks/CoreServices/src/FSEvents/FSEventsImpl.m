/*
 This file is part of Darling.

 Copyright (C) 2020 Lubos Dolezel

 Darling is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 Darling is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with Darling.  If not, see <http://www.gnu.org/licenses/>.
*/

#import "FSEventsImpl.h"
#import <Foundation/NSData.h>
#import <Foundation/NSPathUtilities.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdlib.h>
#include <errno.h>
#include <string.h>
#include <math.h>
#include <stdint.h>
#include <time.h>
#include <stdio.h>
#include <poll.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <darling/emulation/linux_premigration/ext/sys/inotify.h>

// These objects own copies, never the worker's mutable event buffers.
@interface FSEventsBatch : NSObject {
@public
    NSArray* paths;
    NSData* flags;
    NSData* ids;
    uint64_t serial;
}
@end
@implementation FSEventsBatch
-(void)dealloc { [paths release]; [flags release]; [ids release]; [super dealloc]; }
@end

@interface FSEventsRunLoopContext : NSObject {
@public
    __weak FSEventsImpl* stream;
}
@end
@implementation FSEventsRunLoopContext
@end

@interface FSEventsImpl ()
-(void)_state:(void (^)(void))action;
-(void)_invalidateState;
-(void)_readEvents;
-(void)_appendPath:(NSString*)path flags:(FSEventStreamEventFlags)flags eventId:(uint64_t)eventId;
-(void)_drainThroughBarrier;
-(BOOL)_readPackets;
-(void)_armTimer;
-(void)_dispatchEvents;
-(void)_wakeDelivery;
-(void)_deliverEpoch:(NSUInteger)epoch;
-(void)_deliverEpoch:(NSUInteger)epoch until:(FSEventStreamEventId)limit allowReentry:(BOOL)allowReentry;
@end

static char stateQueueKey;
static uint64_t monotonicNS(void) {
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) abort();
    return (uint64_t)now.tv_sec * NSEC_PER_SEC + now.tv_nsec;
}
static const void* retainContext(const void* value) { return [(id)value retain]; }
static void releaseContext(const void* value) { [(id)value release]; }
static void rlPerform(void* value) {
    @autoreleasepool {
        FSEventsImpl* owner = ((FSEventsRunLoopContext*)value)->stream;
        [owner _doCallback];
    }
}
static void wakeLoop(const void* value, void* ignored) { CFRunLoopWakeUp((CFRunLoopRef)value); }

@implementation FSEventsImpl
-(instancetype)initWithPaths:(NSArray*)pathsToWatch
                       flags:(FSEventStreamCreateFlags)flags
                   sinceWhen:(FSEventStreamEventId)sinceWhen
                     latency:(CFTimeInterval)latency
                     context:(FSEventStreamContext*)context
                    callback:(FSEventStreamCallback)callback
{
    self = [super init];
    if (!self) return nil;
    _fd = -1;
    if (!callback || ![pathsToWatch count] || !isfinite(latency) || latency < 0 ||
        (context && context->version != 0)) {
        [self release]; errno = EINVAL; return nil;
    }
    _flags = flags; _callback = callback; _latency = latency;

    _pathsToWatch = [pathsToWatch copy];
    _callbackLock = [[NSRecursiveLock alloc] init];
    _deliveryCondition = [[NSCondition alloc] init];
    _pathArray = [[NSMutableArray alloc] init];
    _deliveryBatches = [[NSMutableArray alloc] init];
    _runloops = CFBagCreateMutable(NULL, 0, &kCFTypeBagCallBacks);
    _stateQueue = dispatch_queue_create("org.darling.FSEvents.state", DISPATCH_QUEUE_SERIAL);
    dispatch_queue_set_specific(_stateQueue, &stateQueueKey, self, NULL);
    _fd = open("/dev/fsevents", O_RDONLY | O_NONBLOCK | O_CLOEXEC);
    if (_fd < 0) { int saved=errno; [self release]; errno=saved; return nil; }
    for (id path in _pathsToWatch) {
        if (![path isKindOfClass:[NSString class]] || ![path isAbsolutePath]) {
            [self release]; errno=EINVAL; return nil;
        }
        const char* text=[path UTF8String];
        if (!text || strlen(text)!=[path lengthOfBytesUsingEncoding:NSUTF8StringEncoding]) {
            [self release]; errno=EINVAL; return nil;
        }
        int directory=open(text,O_RDONLY|O_DIRECTORY|O_CLOEXEC);
        if(directory<0){int saved=errno;[self release];errno=saved;return nil;}
        struct Root {uint64_t path;uint32_t length;int32_t descriptor;} args={(uintptr_t)text,(uint32_t)strlen(text)+1,directory};
        int result=ioctl(_fd,0x80107370,&args);int saved=errno;close(directory);
        if(result<0){[self release];errno=saved;return nil;}
    }
    struct Start {uint64_t since;uint32_t flags,reserved;} begin={sinceWhen,flags,0};
    if(ioctl(_fd,0x80107371,&begin)<0){int saved=errno;[self release];errno=saved;return nil;}
    if (context) {
        _context = *context;
        if (_context.retain) _context.info = (void*)_context.retain(_context.info);
    }
    FSEventsRunLoopContext* box = [[FSEventsRunLoopContext alloc] init];
    box->stream = self;
    CFRunLoopSourceContext rlcontext = {0};
    rlcontext.info = box; rlcontext.perform = rlPerform;
    rlcontext.retain = retainContext; rlcontext.release = releaseContext;
    _rlSource = CFRunLoopSourceCreate(NULL, 0, &rlcontext);
    [box release];
    __weak FSEventsImpl* weakSelf = self;
    _source = dispatch_source_create(DISPATCH_SOURCE_TYPE_READ, _fd, 0, _stateQueue);
    int ownedFD = _fd;
    dispatch_source_set_cancel_handler(_source, ^{ close(ownedFD); });
    dispatch_source_set_event_handler(_source, ^{
        @autoreleasepool { FSEventsImpl* owner = weakSelf; [owner _readEvents]; }
    });
    _timer = dispatch_source_create(DISPATCH_SOURCE_TYPE_TIMER, 0, 0, _stateQueue);
    dispatch_source_set_timer(_timer, DISPATCH_TIME_FOREVER, DISPATCH_TIME_FOREVER, 0);
    dispatch_source_set_event_handler(_timer, ^{
        @autoreleasepool { FSEventsImpl* owner = weakSelf; [owner _dispatchEvents]; }
    });
    dispatch_resume(_timer);
    return self;
}

-(void)_state:(void (^)(void))action
{
    if (!_stateQueue || dispatch_get_specific(&stateQueueKey) == self) action();
    else dispatch_sync(_stateQueue, action);
}

-(void)dealloc
{
    [self invalidate];
    if (_fd >= 0) close(_fd);
    if (_stateQueue) dispatch_release(_stateQueue);
    if (_rlSource) CFRelease(_rlSource);
    if (_runloops) CFRelease(_runloops);
    if (_context.release) _context.release(_context.info);
    [_pathsToWatch release]; [_wdMap release]; [_pathArray release];
    [_deliveryBatches release]; [_callbackLock release]; [_deliveryCondition release];
    free(_flagArray); free(_idArray);
    [super dealloc];
}

-(NSArray*)copyPathsToWatch { return [_pathsToWatch copy]; }

-(void)setDispatchQueue:(dispatch_queue_t)queue
{
    if (queue) dispatch_retain(queue);
    dispatch_queue_t old;
    @synchronized(self) {
        if (_invalidated) { if (queue) dispatch_release(queue); return; }
        old = _queue;
        if (old && old != queue) dispatch_queue_set_specific(old, self, NULL, NULL);
        _queue = queue;
        if (queue) dispatch_queue_set_specific(queue, self, self, NULL);
        ++_deliveryEpoch;
    }
    if (old) dispatch_release(old);
    [self _wakeDelivery];
}

-(void)scheduleWithRunLoop:(CFRunLoopRef)rl mode:(CFStringRef)mode
{
    @synchronized(self) {
        if (_invalidated) return;
        CFBagAddValue(_runloops, rl);
    }
    CFRunLoopAddSource(rl, _rlSource, mode);
    [self _wakeDelivery];
}

-(void)unscheduleWithRunLoop:(CFRunLoopRef)rl mode:(CFStringRef)mode
{
    @synchronized(self) {
        CFBagRemoveValue(_runloops, rl);
    }
    CFRunLoopRemoveSource(rl, _rlSource, mode);
}

-(void)_invalidateState
{
    @synchronized(self) {
        if (_invalidated) return;
        _invalidated = true; _running = false; ++_deliveryEpoch;
        if (_queue) { dispatch_queue_set_specific(_queue, self, NULL, NULL); dispatch_release(_queue); _queue = NULL; }
        if (_runloops) CFBagRemoveAllValues(_runloops);
        [_deliveryBatches removeAllObjects];
    }
    // CoreFoundation may take run-loop/source locks. Never hold the stream
    // monitor while calling into its scheduling or invalidation operations.
    if (_rlSource) CFRunLoopSourceInvalidate(_rlSource);
    [_deliveryCondition lock]; _deliveryInterrupted = true;
    [_deliveryCondition broadcast]; [_deliveryCondition unlock];
    [_pathArray removeAllObjects];
    if (_timer) { dispatch_source_cancel(_timer); dispatch_release(_timer); _timer = NULL; }
    if (_source) {
        dispatch_source_cancel(_source);
        if (!_sourceResumed) dispatch_resume(_source);
        dispatch_release(_source); _source = NULL;
        _fd = -1; // The cancel handler closes it after all source reads finish.
    }
}

-(void)invalidate
{
    __unsafe_unretained FSEventsImpl* owner = self;
    [self _state:^{ [owner _invalidateState]; }];
    // A callback may invalidate its own stream. The recursive lock permits it;
    // other threads wait until any already active callback is finished.
    [_callbackLock lock]; [_callbackLock unlock];
}

-(BOOL)start
{
    __block BOOL started = NO;
    [self _state:^{
        @synchronized(self) {
            if (_invalidated || (!_queue && !CFBagGetCount(_runloops))) return;
            _running = true; started = YES;
        }
        [_deliveryCondition lock]; _deliveryInterrupted = false; [_deliveryCondition unlock];
        if (!_sourceResumed) { dispatch_resume(_source); _sourceResumed = true; }
        [self _readEvents];
        [self _wakeDelivery];
    }];
    return started;
}

-(void)stop
{
    [self _state:^{
        @synchronized(self) { _running = false; }
        if (_sourceResumed) { dispatch_suspend(_source); _sourceResumed = false; }
        if (_timer) dispatch_source_set_timer(_timer, DISPATCH_TIME_FOREVER, DISPATCH_TIME_FOREVER, 0);
        _timerArmed = false;
        [_deliveryCondition lock]; _deliveryInterrupted = true;
        [_deliveryCondition broadcast]; [_deliveryCondition unlock];
    }];
    [_callbackLock lock]; [_callbackLock unlock];
}

-(FSEventStreamEventId)lastEventID
{
    __block FSEventStreamEventId result;
    [self _state:^{ result = _lastEventID; }];
    return result;
}

-(FSEventStreamEventId)flushAsync
{
    __block FSEventStreamEventId result;
    [self _state:^{
        if (_running && !_invalidated) { [self _drainThroughBarrier]; [self _dispatchEvents]; }
        result = _lastEventID;
    }];
    return result;
}

-(void)flushSync
{
    __block FSEventStreamEventId target = 0;
    __block dispatch_queue_t queue = NULL;
    __block NSUInteger epoch = 0;
    __block BOOL valid = NO;
    [self _state:^{
        if (!_running || _invalidated) return;
        [self _drainThroughBarrier]; [self _dispatchEvents];
        target = _lastQueuedSerial; valid = YES;
        @synchronized(self) {
            epoch = _deliveryEpoch;
            if (_queue) { queue = _queue; dispatch_retain(queue); }
        }
    }];
    if (!valid || !target) { if (queue) dispatch_release(queue); return; }
    if (queue) {
        if (dispatch_get_specific(self) == self)
            [self _deliverEpoch:epoch until:target allowReentry:YES];
        else dispatch_sync(queue, ^{
            @autoreleasepool { [self _deliverEpoch:epoch until:target allowReentry:YES]; }
        });
        dispatch_release(queue);
    } else {
        BOOL ownLoop;
        CFRunLoopRef currentLoop = CFRunLoopGetCurrent();
        @synchronized(self) { ownLoop = CFBagContainsValue(_runloops, currentLoop); }
        if (ownLoop) [self _deliverEpoch:epoch until:target allowReentry:YES];
    }
    @synchronized(self) {
        // An already active callback counts as invoked. A recursive sync flush
        // must not wait for its own outer callback frame to return.
        if (_callbackDepth && pthread_equal(_callbackThread, pthread_self()) && _lastInvokedSerial >= target) return;
    }
    [_deliveryCondition lock];
    while (_lastCompletedSerial < target && !_deliveryInterrupted) {
        [_deliveryCondition wait];
    }
    [_deliveryCondition unlock];
}

-(void)_appendPath:(NSString*)path flags:(FSEventStreamEventFlags)flags eventId:(uint64_t)eventId
{
    size_t count = [_pathArray count];
    if (count == _capacity) {
        size_t capacity = _capacity ? _capacity * 2 : 64;
        FSEventStreamEventFlags* newFlags = malloc(capacity * sizeof(*newFlags));
        FSEventStreamEventId* newIDs = malloc(capacity * sizeof(*newIDs));
        if (!newFlags || !newIDs) { free(newFlags); free(newIDs); abort(); }
        if (count) { memcpy(newFlags, _flagArray, count * sizeof(*newFlags)); memcpy(newIDs, _idArray, count * sizeof(*newIDs)); }
        free(_flagArray); free(_idArray); _flagArray = newFlags; _idArray = newIDs; _capacity = capacity;
    }
    [_pathArray addObject:path]; _flagArray[count] = flags; _idArray[count] = eventId;
    _lastEventID=eventId;
}

// Each read consumes one complete sequenced packet. IDs come from the same
// server journal as FSEventsGetCurrentEventId; callbacks never allocate IDs.
-(BOOL)_readPackets
{
    if (!_running || _invalidated || _fd<0) return NO;
    const size_t capacity=65536;
    char* bytes=malloc(capacity); if(!bytes)abort();
    BOOL healthy=YES;
    @try {
        for(;;){
            ssize_t count=read(_fd,bytes,capacity);
            if(count<0){if(errno==EINTR)continue;if(errno==EAGAIN||errno==EWOULDBLOCK)break;healthy=NO;break;}
            if(!count){healthy=NO;break;}
            struct Header {uint32_t magic,length;uint64_t id;uint32_t flags,reserved;} header;
            if(count<sizeof header){healthy=NO;break;}
            memcpy(&header,bytes,sizeof header);
            if(header.magic!=0x314a5346||header.reserved||header.length!=(size_t)count-sizeof header){healthy=NO;break;}
            if(header.flags==0x80000000u){
                if(header.length){healthy=NO;break;}
                if(header.id>_lastBarrier)_lastBarrier=header.id;
                continue;
            }
            if((!header.id&&!(header.flags&kFSEventStreamEventFlagRootChanged))||!header.length||bytes[count-1]||memchr(bytes+sizeof header,0,header.length-1)){healthy=NO;break;}
            NSString* path=[NSString stringWithUTF8String:bytes+sizeof header];
            if(path)[self _appendPath:path flags:header.flags eventId:header.id];
            else for(NSString* root in _pathsToWatch)
                [self _appendPath:root flags:kFSEventStreamEventFlagMustScanSubDirs|kFSEventStreamEventFlagUserDropped eventId:header.id];
        }
    } @finally {free(bytes);}
    if(!healthy){
        @synchronized(self){_running=false;}
        if(_sourceResumed){dispatch_suspend(_source);_sourceResumed=false;}
        [_deliveryCondition lock];_deliveryInterrupted=true;[_deliveryCondition broadcast];[_deliveryCondition unlock];
    }
    return healthy;
}
-(void)_readEvents
{
    [self _readPackets];
    if([_pathArray count])[self _armTimer];
}
-(void)_drainThroughBarrier
{
    if(!_running||_invalidated||_fd<0)return;
    uint64_t ticket=0;
    if(ioctl(_fd,0x40087372,&ticket)<0)return;
    uint64_t deadline=monotonicNS()+30*NSEC_PER_SEC;
    while(_lastBarrier<ticket){
        if(![self _readPackets])break;
        if(_lastBarrier>=ticket)break;
        struct pollfd descriptor={_fd,POLLIN,0};
        int result=poll(&descriptor,1,1000);
        if(result<0&&errno!=EINTR)break;
        if(monotonicNS()>deadline)break;
    }
}

-(void)_armTimer
{
    if (_timerArmed || !_running || _invalidated) return;
    if (_latency == 0) { [self _dispatchEvents]; return; }
    uint64_t interval = _latency >= (double)(INT64_MAX / NSEC_PER_SEC)
        ? INT64_MAX : (uint64_t)(_latency * NSEC_PER_SEC);
    uint64_t delay = interval;
    if (_flags & kFSEventStreamCreateFlagNoDefer) {
        uint64_t now = monotonicNS();
        if (!_lastDispatchNS || now - _lastDispatchNS >= interval) {
            [self _dispatchEvents]; return;
        }
        delay = interval - (now - _lastDispatchNS);
    }
    _timerArmed = true;
    dispatch_source_set_timer(_timer, dispatch_time(DISPATCH_TIME_NOW, (int64_t)delay), DISPATCH_TIME_FOREVER, 0);
}

-(void)_dispatchEvents
{
    if (!_running || _invalidated || ![_pathArray count]) return;
    _timerArmed = false; _lastDispatchNS = monotonicNS();
    dispatch_source_set_timer(_timer, DISPATCH_TIME_FOREVER, DISPATCH_TIME_FOREVER, 0);
    FSEventsBatch* batch = [[FSEventsBatch alloc] init];
    batch->serial = ++_lastQueuedSerial;
    batch->paths = [_pathArray copy];
    batch->flags = [[NSData alloc] initWithBytes:_flagArray length:[_pathArray count]*sizeof(*_flagArray)];
    batch->ids = [[NSData alloc] initWithBytes:_idArray length:[_pathArray count]*sizeof(*_idArray)];
    [_pathArray removeAllObjects];
    @synchronized(self) { [_deliveryBatches addObject:batch]; }
    [batch release];
    [self _wakeDelivery];
}

-(void)_wakeDelivery
{
    dispatch_queue_t queue = NULL; NSUInteger epoch;
    CFRunLoopSourceRef source = NULL; const void** loops = NULL; CFIndex count = 0;
    @synchronized(self) {
        if (_invalidated || !_running || ![_deliveryBatches count]) return;
        epoch = _deliveryEpoch;
        if (_queue) { queue = _queue; dispatch_retain(queue); }
        else if (_rlSource) {
            source = (CFRunLoopSourceRef)CFRetain(_rlSource);
            count = CFBagGetCount(_runloops);
            if (count) {
                loops = malloc(count * sizeof(*loops)); if (!loops) abort();
                CFBagGetValues(_runloops, loops);
                for (CFIndex i=0; i<count; ++i) CFRetain(loops[i]);
            }
        }
    }
    if (source) {
        CFRunLoopSourceSignal(source);
        for (CFIndex i=0; i<count; ++i) { wakeLoop(loops[i], NULL); CFRelease(loops[i]); }
        free(loops); CFRelease(source);
    }
    if (queue) {
        __weak FSEventsImpl* weakSelf = self;
        dispatch_async(queue, ^{ @autoreleasepool { FSEventsImpl* owner = weakSelf; [owner _deliverEpoch:epoch]; } });
        dispatch_release(queue);
    }
}

-(void)_doCallback
{
    NSUInteger epoch;
    @synchronized(self) { if (_queue) return; epoch = _deliveryEpoch; }
    [self _deliverEpoch:epoch];
}

-(void)_deliverEpoch:(NSUInteger)epoch
{
    [self _deliverEpoch:epoch until:UINT64_MAX allowReentry:NO];
}

-(void)_deliverEpoch:(NSUInteger)epoch until:(FSEventStreamEventId)limit allowReentry:(BOOL)allowReentry
{
    [_callbackLock lock];
    if (_delivering && !allowReentry) { [_callbackLock unlock]; return; }
    BOOL wasDelivering = _delivering;
    _delivering = true;
    @try {
        for (;;) {
            FSEventsBatch* batch = nil;
            @synchronized(self) {
                if (_invalidated || !_running || epoch != _deliveryEpoch || _lastInvokedSerial >= limit || ![_deliveryBatches count]) break;
                batch = [[_deliveryBatches objectAtIndex:0] retain];
                [_deliveryBatches removeObjectAtIndex:0];
            }
            @try {
                NSUInteger count = [batch->paths count];
                void* payload = batch->paths; char** cpaths = NULL; NSArray* extended = nil;
                if (!(_flags & kFSEventStreamCreateFlagUseCFTypes)) {
                    cpaths = calloc(count, sizeof(*cpaths)); if (!cpaths) abort();
                    for (NSUInteger i=0; i<count; ++i) { cpaths[i] = strdup([[batch->paths objectAtIndex:i] UTF8String]); if (!cpaths[i]) abort(); }
                    payload = cpaths;
                } else if (_flags & kFSEventStreamCreateFlagUseExtendedData) {
                    NSMutableArray* values = [[NSMutableArray alloc] initWithCapacity:count];
                    for (NSString* path in batch->paths) [values addObject:@{(NSString*)kFSEventStreamEventExtendedDataPathKey:path}];
                    extended = values; payload = extended;
                }
                uint64_t last = batch->serial;
                @synchronized(self) { _callbackThread = pthread_self(); ++_callbackDepth; if (last > _lastInvokedSerial) _lastInvokedSerial = last; }
                @try {
                    _callback((ConstFSEventStreamRef)self, _context.info, count, payload, [batch->flags bytes], [batch->ids bytes]);
                } @finally {
                    @synchronized(self) { --_callbackDepth; }
                    [_deliveryCondition lock];
                    if (last > _lastCompletedSerial) _lastCompletedSerial = last;
                    [_deliveryCondition broadcast]; [_deliveryCondition unlock];
                    if (cpaths) { for (NSUInteger i=0; i<count; ++i) free(cpaths[i]); free(cpaths); }
                    [extended release];
                }
            } @finally { [batch release]; }
        }
    } @finally { _delivering = wasDelivering; [_callbackLock unlock]; }
}
@end
