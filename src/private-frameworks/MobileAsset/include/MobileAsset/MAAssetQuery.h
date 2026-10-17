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

#include <Foundation/Foundation.h>

#import <MobileAsset/MAAsset.h>

// seems to be implicitly depended on by `OTATrustUtilities.m` in Security
#import <MobileAsset/ASAssetQuery.h>

/* Values and method ABI verified against the original Intel framework. */
typedef NS_ENUM(NSInteger, MAQueryResult) {
    MAQuerySuccessful = 0, MAQueryXpcError = 1, MAQueryCatalogNotDownloaded = 2,
    MAQueryFailed = 3, MAQueryDaemonExit = 4, MAQueryNotEntitled = 5,
    MAQueryCannotCreateMessage = 6, MAQueryNilAssetType = 7,
    MAQueryParamsEncodeFailure = 8, MAQueryBeforeFirstUnlock = 9,
    MAQueryCouldNotEncodeResults = 10, MAQueryXpcLengthError = 11,
    MAQueryUnknownResult = 12, MAQueryTooManyResults = 13, MAQueryHasAllowedDifferences = 14,
};
typedef NS_ENUM(NSInteger, MAQueryReturnTypes) {
    MACatalogOnly = 0, MAInstalledOnly = 1, MAUnionOfCatalogInstalled = 2,
    MAPreinstalledOnly = 3, MACatalogButNotInstalledOnly = 4,
    MAStrictlyCatalogOnly = 5, MAStrictlyObsoleteOnly = 6,
};
@interface MAAssetQuery : NSObject
- (instancetype)initWithType:(NSString*)assetType;
- (instancetype)initWithType:(NSString*)assetType andPurpose:(NSString*)purpose;
- (NSInteger)addKeyValuePair:(NSString*)key with:(NSString*)value;
- (NSInteger)addKeyValueArray:(NSString*)key with:(NSArray*)values;
- (NSInteger)addKeyValueNull:(NSString*)key;
- (void)returnTypes:(MAQueryReturnTypes)types;
- (MAQueryReturnTypes)returnTypes;
- (MAQueryResult)queryMetaDataSync;
- (void)queryMetaData:(void (^)(MAQueryResult result))completion;
- (void)queryMetaDataWithError:(void (^)(MAQueryResult result, NSError* error))completion;
@property (readonly) NSString* assetType;
@property (copy) NSString* purpose;
@property (readonly) NSArray* queryParams;
@property (readonly) NSArray<MAAsset*>* results;
@property (readonly) NSSet<NSString*>* assetIds;
@property (readonly) MAQueryResult resultCode;
@property (readonly) BOOL isDone;
@property BOOL doNotBlockBeforeFirstUnlock;
@property BOOL doNotBlockOnNetworkStatus;
@property (readonly) NSDate* postedDate;
@property (readonly) NSDate* lastFetchDate;
- (char)isCatalogFetchedFromLiveServer;
@end
