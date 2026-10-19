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
#include <dirent.h>
#include <sys/stat.h>
#include <darling/emulation/linux_premigration/ext/sys/inotify.h>

// These objects own copies, never the worker's mutable event buffers.
@interface FSEventsBatch : NSObject {
@public
    NSArray* paths;
    NSData* flags;
    NSData* ids;
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
-(void)_processSingleEvent:(struct inotify_event*)event;
-(void)_appendPath:(NSString*)path flags:(FSEventStreamEventFlags)flags;
-(BOOL)_watchTree:(NSString*)path map:(NSMutableDictionary*)map root:(BOOL)root;
-(void)_refreshWatches;
-(void)_coverageLost;
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
    _historyPending = sinceWhen != kFSEventStreamEventIdSinceNow;
    _pathsToWatch = [pathsToWatch copy];
    _callbackLock = [[NSRecursiveLock alloc] init];
    _deliveryCondition = [[NSCondition alloc] init];
    _pathArray = [[NSMutableArray alloc] init];
    _deliveryBatches = [[NSMutableArray alloc] init];
    _runloops = CFBagCreateMutable(NULL, 0, &kCFTypeBagCallBacks);
    _stateQueue = dispatch_queue_create("org.darling.FSEvents.state", DISPATCH_QUEUE_SERIAL);
    dispatch_queue_set_specific(_stateQueue, &stateQueueKey, self, NULL);
    _fd = inotify_init1(IN_NONBLOCK);
    if (_fd < 0) { int saved = errno; [self release]; errno = saved; return nil; }
    if (fcntl(_fd, F_SETFD, FD_CLOEXEC) < 0) {
        int saved = errno; [self release]; errno = saved; return nil;
    }
    NSMutableDictionary* watches = [[NSMutableDictionary alloc] init];
    for (id path in _pathsToWatch) {
        if (![path isKindOfClass:[NSString class]]) {
            [watches release]; [self release]; errno = EINVAL; return nil;
        }
        if (![self _watchTree:path map:watches root:YES]) {
            int saved = errno; [watches release]; [self release]; errno = saved; return nil;
        }
    }
    _wdMap = watches;
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

// Watch each directory before listing it. Work iteratively: dispatch workers
// can have small stacks, and SDK trees can be deeply nested. Child symlinks
// are reported by their parent, not followed into cycles or unrelated trees.
-(BOOL)_watchTree:(NSString*)path map:(NSMutableDictionary*)map root:(BOOL)root
{
    NSMutableArray* pending = [[NSMutableArray alloc] initWithObjects:path, nil];
    BOOL ok = YES;
    while ([pending count]) {
        @autoreleasepool {
            NSString* item = [[[pending lastObject] retain] autorelease];
            [pending removeLastObject];
            struct stat st;
            if (lstat([item UTF8String], &st) < 0) {
                if (!root && errno == ENOENT) continue;
                ok = NO; break;
            }
            if (S_ISLNK(st.st_mode)) {
                if (root && [item isEqualToString:path]) {
                    char* resolved = realpath([item UTF8String], NULL);
                    if (!resolved) { ok = NO; break; }
                    NSString* target = [NSString stringWithUTF8String:resolved];
                    free(resolved);
                    if (!target) { errno = EILSEQ; ok = NO; break; }
                    [pending addObject:target];
                }
                continue;
            }
            if (!S_ISDIR(st.st_mode) && ![item isEqualToString:path]) continue;
            if ([map count] >= 65536) { errno = ENOSPC; ok = NO; break; }
            int wd = inotify_add_watch(_fd, [item UTF8String],
                IN_ATTRIB | IN_CREATE | IN_DELETE | IN_DELETE_SELF | IN_MODIFY |
                IN_MOVE | IN_UNMOUNT | IN_DONT_FOLLOW |
                (S_ISDIR(st.st_mode) ? IN_ONLYDIR : 0));
            if (wd < 0) { ok = NO; break; }
            [map setObject:item forKey:[NSNumber numberWithInt:wd]];
            if (!S_ISDIR(st.st_mode)) continue;
            DIR* directory = opendir([item UTF8String]);
            if (!directory) { ok = NO; break; }
            int saved = 0;
            for (;;) {
                errno = 0;
                struct dirent* entry = readdir(directory);
                if (!entry) { saved = errno; break; }
                if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, "..")) continue;
                // A directory watch already covers ordinary files. Avoid one
                // extra emulated lstat per SDK file just to discard it; retain
                // the lstat fallback when the filesystem has no d_type data.
                if (entry->d_type != DT_DIR && entry->d_type != DT_UNKNOWN) continue;
                NSString* leaf = [NSString stringWithUTF8String:entry->d_name];
                if (!leaf) { saved = EILSEQ; break; }
                [pending addObject:[item stringByAppendingPathComponent:leaf]];
            }
            closedir(directory);
            if (saved) { errno = saved; ok = NO; break; }
        }
    }
    int saved = errno;
    [pending release];
    errno = saved;
    return ok;
}

-(void)_coverageLost
{
    for (NSString* path in _pathsToWatch)
        [self _appendPath:path flags:kFSEventStreamEventFlagMustScanSubDirs |
                                   kFSEventStreamEventFlagUserDropped];
}

-(void)_refreshWatches
{
    NSMutableDictionary* fresh = [[NSMutableDictionary alloc] init];
    for (NSString* path in _pathsToWatch)
        if (![self _watchTree:path map:fresh root:YES]) [self _coverageLost];
    for (NSNumber* wd in _wdMap)
        if (![fresh objectForKey:wd]) inotify_rm_watch(_fd, [wd intValue]);
    [_wdMap release]; _wdMap = fresh;
    _watchRefreshPending = false;
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
        if (_historyPending) {
            // No durable journal is available in this backend. Never present
            // an unobserved interval as an unchanged tree: consumers must scan.
            [self _coverageLost];
        }
        [self _readEvents];
        if (_historyPending) {
            _historyPending = false;
            [self _appendPath:[_pathsToWatch objectAtIndex:0]
                        flags:kFSEventStreamEventFlagHistoryDone];
            [self _dispatchEvents];
        }
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
        if (_running && !_invalidated) { [self _readEvents]; [self _dispatchEvents]; }
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
        [self _readEvents]; [self _dispatchEvents];
        target = _lastEventID; valid = YES;
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
        if (_callbackDepth && pthread_equal(_callbackThread, pthread_self()) && _lastInvokedID >= target) return;
    }
    [_deliveryCondition lock];
    while (_lastCompletedID < target && !_deliveryInterrupted) {
        [_deliveryCondition wait];
    }
    [_deliveryCondition unlock];
}

-(void)_appendPath:(NSString*)path flags:(FSEventStreamEventFlags)flags
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
    [_pathArray addObject:path]; _flagArray[count] = flags; _idArray[count] = ++_lastEventID;
}

-(void)_processSingleEvent:(struct inotify_event*)event
{
    if (event->mask & IN_Q_OVERFLOW) {
        for (NSString* path in _pathsToWatch)
            [self _appendPath:path flags:kFSEventStreamEventFlagMustScanSubDirs | kFSEventStreamEventFlagKernelDropped];
        return;
    }
    NSString* watchPath = [_wdMap objectForKey:[NSNumber numberWithInt:event->wd]];
    if (!watchPath) return;
    if (event->mask & IN_IGNORED) {
        [_wdMap removeObjectForKey:[NSNumber numberWithInt:event->wd]];
        return;
    }
    FSEventStreamEventFlags flags = 0;
    if (event->mask & IN_UNMOUNT) flags |= kFSEventStreamEventFlagUnmount | kFSEventStreamEventFlagMustScanSubDirs;
    NSString* changedPath = watchPath;
    if (event->len && event->name[0]) {
        NSString* leaf = [NSString stringWithUTF8String:event->name];
        if (!leaf) { [self _coverageLost]; return; }
        changedPath = [watchPath stringByAppendingPathComponent:leaf];
    }
    NSString* fullPath = watchPath;
    if (_flags & kFSEventStreamCreateFlagFileEvents) {
        flags |= (event->mask & IN_ISDIR) ? kFSEventStreamEventFlagItemIsDir : kFSEventStreamEventFlagItemIsFile;
        if (event->mask & (IN_DELETE | IN_DELETE_SELF)) flags |= kFSEventStreamEventFlagItemRemoved;
        if (event->mask & (IN_MOVE_SELF | IN_MOVED_FROM | IN_MOVED_TO)) flags |= kFSEventStreamEventFlagItemRenamed;
        if (event->mask & IN_MODIFY) flags |= kFSEventStreamEventFlagItemModified;
        if (event->mask & IN_CREATE) flags |= kFSEventStreamEventFlagItemCreated;
        if (event->mask & IN_ATTRIB) flags |= kFSEventStreamEventFlagItemChangeOwner | kFSEventStreamEventFlagItemXattrMod;
        if (event->len && event->name[0]) fullPath = changedPath;
    }
    [self _appendPath:fullPath flags:flags];
    if ((event->mask & IN_ISDIR) && (event->mask & (IN_CREATE | IN_MOVED_TO))) {
        // Changes before the new subtree's watches were installed are unknown.
        // Scan notification closes that race instead of fabricating events.
        [self _coverageLost];
        if (event->mask & IN_MOVED_TO) [self _refreshWatches];
        else if (![self _watchTree:changedPath map:_wdMap root:NO]) [self _coverageLost];
    }
    if (((event->mask & IN_ISDIR) && (event->mask & (IN_MOVED_FROM | IN_DELETE))) ||
        (event->mask & (IN_DELETE_SELF | IN_MOVE_SELF | IN_UNMOUNT))) {
        _watchRefreshPending = true;
        [self _coverageLost];
    }
}

-(void)_readEvents
{
    if (!_running || _invalidated || _fd < 0) return;
    // Dispatch workers may have small stacks with an internal guard page.
    // A 64 KiB automatic buffer can skip that guard and fault on the next
    // Objective-C call. malloc supplies sufficient inotify_event alignment.
    const size_t capacity = 65536;
    char* buffer = malloc(capacity);
    if (!buffer) abort();
    @try {
    for (;;) {
        ssize_t count = read(_fd, buffer, capacity);
        if (count < 0) {
            if (errno == EINTR) continue;
            if (errno != EAGAIN && errno != EWOULDBLOCK) {
                @synchronized(self) { _running = false; }
                if (_sourceResumed) { dispatch_suspend(_source); _sourceResumed = false; }
                [_deliveryCondition lock]; _deliveryInterrupted = true;
                [_deliveryCondition broadcast]; [_deliveryCondition unlock];
            }
            break;
        }
        if (!count) break;
        size_t offset = 0;
        while (offset < (size_t)count) {
            if ((size_t)count - offset < sizeof(struct inotify_event)) break;
            struct inotify_event* event = (void*)(buffer + offset);
            if (event->len > (size_t)count - offset - sizeof(*event)) break;
            if (event->len && !memchr(event->name, 0, event->len)) break;
            [self _processSingleEvent:event]; offset += sizeof(*event) + event->len;
        }
    }
    } @finally { free(buffer); }
    if (_watchRefreshPending) [self _refreshWatches];
    if ([_pathArray count]) [self _armTimer];
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
                if (_invalidated || !_running || epoch != _deliveryEpoch || _lastInvokedID >= limit || ![_deliveryBatches count]) break;
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
                FSEventStreamEventId last = ((const FSEventStreamEventId*)[batch->ids bytes])[count-1];
                @synchronized(self) { _callbackThread = pthread_self(); ++_callbackDepth; if (last > _lastInvokedID) _lastInvokedID = last; }
                @try {
                    _callback((ConstFSEventStreamRef)self, _context.info, count, payload, [batch->flags bytes], [batch->ids bytes]);
                } @finally {
                    @synchronized(self) { --_callbackDepth; }
                    [_deliveryCondition lock];
                    if (last > _lastCompletedID) _lastCompletedID = last;
                    [_deliveryCondition broadcast]; [_deliveryCondition unlock];
                    if (cpaths) { for (NSUInteger i=0; i<count; ++i) free(cpaths[i]); free(cpaths); }
                    [extended release];
                }
            } @finally { [batch release]; }
        }
    } @finally { _delivering = wasDelivering; [_callbackLock unlock]; }
}
@end
