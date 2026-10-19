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

#import <Foundation/NSObject.h>
#import <Foundation/NSArray.h>
#import <Foundation/NSString.h>
#import <Foundation/NSDictionary.h>
#import <Foundation/NSLock.h>
#include <CoreFoundation/CFBag.h>
#include <FSEvents/FSEvents.h>
#include <dispatch/dispatch.h>
#include <pthread.h>

@interface FSEventsImpl : NSObject
{
	NSArray<NSString*>* _pathsToWatch;
	NSMutableDictionary<NSNumber*, NSString*>* _wdMap;

	FSEventStreamCreateFlags _flags;
	FSEventStreamContext _context;
	FSEventStreamCallback _callback;
	dispatch_source_t _source;
	dispatch_queue_t _queue;
	CFMutableBagRef _runloops;
	CFRunLoopSourceRef _rlSource;
	int _fd;
	FSEventStreamEventId _lastEventID;
	bool _running;

	NSMutableArray* _pathArray;
	FSEventStreamEventFlags* _flagArray;
	FSEventStreamEventId* _idArray;

	// State and FD access are serialized separately from client callbacks.
	dispatch_queue_t _stateQueue;
	dispatch_source_t _timer;
	CFTimeInterval _latency;
	uint64_t _lastDispatchNS;
	bool _sourceResumed;
	bool _invalidated;
	bool _timerArmed;
	bool _delivering;
	size_t _capacity;
	NSUInteger _deliveryEpoch;
	NSMutableArray* _deliveryBatches;
	NSRecursiveLock* _callbackLock;
	NSCondition* _deliveryCondition;
	FSEventStreamEventId _lastCompletedID;
	FSEventStreamEventId _lastInvokedID;
	bool _deliveryInterrupted;
	pthread_t _callbackThread;
	unsigned _callbackDepth;
	bool _historyPending;
	bool _watchRefreshPending;
}

-(instancetype)initWithPaths:(NSArray*)pathsToWatch
						flags:(FSEventStreamCreateFlags)flags
                      sinceWhen:(FSEventStreamEventId)sinceWhen
                        latency:(CFTimeInterval)latency
					context:(FSEventStreamContext*)context
					callback:(FSEventStreamCallback)callback;
-(NSArray*)copyPathsToWatch;

-(void)setDispatchQueue:(dispatch_queue_t)queue;
-(void)scheduleWithRunLoop:(CFRunLoopRef)rl
					mode:(CFStringRef)rlMode;
-(void)unscheduleWithRunLoop:(CFRunLoopRef)rl
					mode:(CFStringRef)rlMode;
-(void)invalidate;
-(BOOL)start;
-(void)stop;
-(FSEventStreamEventId)lastEventID;
-(void)_doCallback;
-(FSEventStreamEventId)flushAsync;
-(void)flushSync;

@end

