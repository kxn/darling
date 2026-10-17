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

#import <MobileAsset/MAAssetQuery.h>
#include <dispatch/dispatch.h>
#include <uuid/uuid.h>
#include <xpc/xpc.h>

static dispatch_queue_t queryCallbackQueue(void)
{
    static dispatch_queue_t queue;
    static dispatch_once_t once;
    dispatch_once(&once, ^{ queue = dispatch_queue_create("com.apple.MobileAsset.query.callbacks", DISPATCH_QUEUE_SERIAL); });
    return queue;
}
static BOOL queryResultFailed(MAQueryResult code)
{
    return code != MAQuerySuccessful && code != MAQueryCatalogNotDownloaded && code != MAQueryHasAllowedDifferences;
}
static NSError* queryError(MAQueryResult code)
{
    if (!queryResultFailed(code)) return nil;
    return [NSError errorWithDomain:@"com.apple.MobileAssetError.Query" code:code
        userInfo:@{NSLocalizedDescriptionKey:[NSString stringWithFormat:@"MobileAsset query failed (%ld)", (long)code]}];
}

@implementation MAAssetQuery {
    NSString* _assetType;
    NSString* _purpose;
    NSMutableArray* _queryParams;
    NSArray* _results;
    NSSet* _assetIds;
    MAQueryReturnTypes _returnTypes;
    MAQueryResult _resultCode;
    BOOL _isDone, _doNotBlockBeforeFirstUnlock, _doNotBlockOnNetworkStatus, _isPallasResult;
    NSDate* _postedDate;
    NSDate* _lastFetchDate;
}
@synthesize assetType = _assetType, purpose = _purpose, results = _results, assetIds = _assetIds;
@synthesize resultCode = _resultCode, isDone = _isDone, postedDate = _postedDate, lastFetchDate = _lastFetchDate;
@synthesize doNotBlockBeforeFirstUnlock = _doNotBlockBeforeFirstUnlock, doNotBlockOnNetworkStatus = _doNotBlockOnNetworkStatus;
- (instancetype)init { return [self initWithType:nil]; }
- (instancetype)initWithType:(NSString*)type { return [self initWithType:type andPurpose:nil]; }
- (instancetype)initWithType:(NSString*)type andPurpose:(NSString*)purpose
{
    if ((self = [super init])) {
        _assetType = [type copy]; _purpose = [purpose copy];
        _queryParams = [[NSMutableArray alloc] init];
        _resultCode = MAQueryUnknownResult;
    }
    return self;
}
- (void)dealloc
{
    [_assetType release]; [_purpose release]; [_queryParams release]; [_results release];
    [_assetIds release]; [_postedDate release]; [_lastFetchDate release]; [super dealloc];
}
- (NSArray*)queryParams { @synchronized(self) { return [[_queryParams copy] autorelease]; } }
- (void)returnTypes:(MAQueryReturnTypes)types { @synchronized(self) { _returnTypes = types; } }
- (MAQueryReturnTypes)returnTypes { @synchronized(self) { return _returnTypes; } }
- (char)isCatalogFetchedFromLiveServer { return _isPallasResult; }
- (NSInteger)addKeyValueArray:(NSString*)key with:(NSArray*)values
{
    if (![key isKindOfClass:[NSString class]] || ![values isKindOfClass:[NSArray class]]) return 1;
    for (id value in values)
        if (![value isKindOfClass:[NSString class]] && value != [NSNull null]) return 1;
    NSDictionary* param = @{ @"queryKey":key, @"queryValue":[[values copy] autorelease] };
    @synchronized(self) { [_queryParams addObject:param]; }
    return 0;
}
- (NSInteger)addKeyValuePair:(NSString*)key with:(NSString*)value
{
    if (![value isKindOfClass:[NSString class]]) return 1;
    return [self addKeyValueArray:key with:@[value]];
}
- (NSInteger)addKeyValueNull:(NSString*)key { return [self addKeyValueArray:key with:@[[NSNull null]]]; }

/* Decode only Foundation property-list classes. Never instantiate arbitrary
 * classes supplied by the peer. No catalog or download success is synthesized. */
- (MAQueryResult)decodeQueryReply:(xpc_object_t)reply
{
    if (!reply || xpc_get_type(reply) != XPC_TYPE_DICTIONARY) return MAQueryXpcError;
    xpc_object_t status = xpc_dictionary_get_value(reply, "Result");
    if (!status || xpc_get_type(status) != XPC_TYPE_INT64) return MAQueryUnknownResult;
    MAQueryResult code = xpc_int64_get_value(status);
    if (queryResultFailed(code)) return code;
    xpc_object_t value = xpc_dictionary_get_value(reply, "xmlData");
    if (!value && code == MAQueryCatalogNotDownloaded) return code;
    if (!value || xpc_get_type(value) != XPC_TYPE_DATA) return MAQueryCouldNotEncodeResults;
    size_t length = 0; const void* bytes = xpc_dictionary_get_data(reply, "xmlData", &length);
    if (!bytes || !length) return MAQueryXpcLengthError;
    @try {
        NSData* data = [NSData dataWithBytes:bytes length:length];
        NSError* error = nil;
        NSSet* allowed = [NSSet setWithObjects:[NSDictionary class], [NSArray class], [NSString class],
            [NSNumber class], [NSDate class], [NSData class], [NSNull class], nil];
        id payload = [NSKeyedUnarchiver unarchivedObjectOfClasses:allowed fromData:data error:&error];
        if (error || ![payload isKindOfClass:[NSDictionary class]]) return MAQueryCouldNotEncodeResults;
        id records = [payload objectForKey:@"assetsToFrameWork"];
        id metadata = [payload objectForKey:@"metaToFrameWork"];
        id catalog = [payload objectForKey:@"catalogInfoToFrameWork"];
        if (![records isKindOfClass:[NSArray class]] ||
            (metadata && ![metadata isKindOfClass:[NSDictionary class]]) ||
            (catalog && ![catalog isKindOfClass:[NSDictionary class]])) return MAQueryCouldNotEncodeResults;
        NSMutableArray* assets = [NSMutableArray array]; NSMutableSet* ids = [NSMutableSet set];
        for (id record in records) {
            if (![record isKindOfClass:[NSDictionary class]]) return MAQueryCouldNotEncodeResults;
            id properties = [record objectForKey:@"AssetProperties"];
            id added = [record objectForKey:@"AssetAddedProperties"];
            if (![properties isKindOfClass:[NSDictionary class]] || ![added isKindOfClass:[NSDictionary class]] ||
                ![[added objectForKey:@"AssetId"] isKindOfClass:[NSString class]] ||
                ![[added objectForKey:@"AssetType"] isKindOfClass:[NSString class]] ||
                ![[added objectForKey:@"AssetState"] isKindOfClass:[NSNumber class]]) return MAQueryCouldNotEncodeResults;
            MAAsset* asset = [[[MAAsset alloc] initWithAttributes:record] autorelease];
            if (!asset) return MAQueryCouldNotEncodeResults;
            [assets addObject:asset]; [ids addObject:asset.assetId];
        }
        id posted = [metadata objectForKey:@"postedDate"], fetched = [metadata objectForKey:@"lastTimeChecked"];
        id live = [catalog objectForKey:@"isLiveServer"];
        if ((posted && ![posted isKindOfClass:[NSDate class]]) || (fetched && ![fetched isKindOfClass:[NSDate class]]) ||
            (live && ![live isKindOfClass:[NSNumber class]])) return MAQueryCouldNotEncodeResults;
        _results = [assets copy]; _assetIds = [ids copy];
        _postedDate = [posted retain]; _lastFetchDate = [fetched retain]; _isPallasResult = [live boolValue];
        return code;
    } @catch (NSException* exception) { return MAQueryCouldNotEncodeResults; }
}

- (MAQueryResult)queryMetaDataSync
{
    @synchronized(self) {
        _isDone = NO; _isPallasResult = NO;
        [_results release]; _results = nil; [_assetIds release]; _assetIds = nil;
        [_postedDate release]; _postedDate = nil; [_lastFetchDate release]; _lastFetchDate = nil;
        MAQueryResult result = MAQueryNilAssetType;
        if ([_assetType isKindOfClass:[NSString class]]) {
            NSError* error = nil;
            NSData* params = [NSKeyedArchiver archivedDataWithRootObject:_queryParams requiringSecureCoding:YES error:&error];
            result = MAQueryParamsEncodeFailure;
            if (params && !error) {
                xpc_object_t request = xpc_dictionary_create(NULL,NULL,0);
                result = MAQueryCannotCreateMessage;
                if (request) {
                    xpc_dictionary_set_string(request,"AssetType",[_assetType UTF8String]);
                    xpc_dictionary_set_int64(request,"messageAction",1);
                    xpc_dictionary_set_int64(request,"returnAssetTypes",_returnTypes);
                    xpc_dictionary_set_bool(request,"doNotBlockBeforeFirstUnlock",_doNotBlockBeforeFirstUnlock);
                    xpc_dictionary_set_bool(request,"doNotBlockOnNetworkStatus",_doNotBlockOnNetworkStatus);
                    xpc_dictionary_set_data(request,"QueryParams",[params bytes],[params length]);
                    if (_purpose) xpc_dictionary_set_string(request,"Purpose",[_purpose UTF8String]);
                    NSString* client = [[NSBundle mainBundle] bundleIdentifier];
                    if (!client) client = [NSString stringWithFormat:@"%s", getprogname()];
                    xpc_dictionary_set_string(request,"clientName",[client UTF8String]);
                    xpc_dictionary_set_string(request,"requestType","requestTypeSync");
                    result = MAQueryXpcError;
                    for (unsigned attempt = 0; attempt < 2; ++attempt) {
                        xpc_connection_t connection = xpc_connection_create("com.apple.mobileassetd.v2",NULL);
                        if (!connection) break;
                        uuid_t identifier; char text[37]; uuid_generate(identifier); uuid_unparse_upper(identifier,text);
                        xpc_dictionary_set_string(request,"connectionIdentifier",text);
                        xpc_connection_set_event_handler(connection, ^(xpc_object_t event) { (void)event; });
                        xpc_connection_resume(connection);
                        xpc_object_t reply = xpc_connection_send_message_with_reply_sync(connection,request);
                        BOOL retry = reply == XPC_ERROR_CONNECTION_INTERRUPTED && attempt == 0;
                        result = [self decodeQueryReply:reply];
                        if (reply) xpc_release(reply);
                        xpc_connection_cancel(connection); xpc_release(connection);
                        if (!retry) break;
                    }
                    xpc_release(request);
                }
            }
        }
        _resultCode = result; _isDone = YES; return result;
    }
}

/* The public asynchronous ABI uses a worker for the real synchronous wire
 * transaction, then the shared serial callback queue. It does not depend on a
 * run loop or on the caller retaining either the query or its stack block. */
- (void)queryMetaDataWithError:(void (^)(MAQueryResult,NSError*))completion
{
    @synchronized(self) { _isDone = NO; }
    dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT,0), ^{
        @autoreleasepool {
            MAQueryResult result = [self queryMetaDataSync];
            NSError* error = queryError(result);
            dispatch_async(queryCallbackQueue(), ^{ @autoreleasepool { if (completion) completion(result,error); } });
        }
    });
}
- (void)queryMetaData:(void (^)(MAQueryResult))completion
{
    [self queryMetaDataWithError:^(MAQueryResult result,NSError* error) { if (completion) completion(result); }];
}
@end
