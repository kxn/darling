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


#ifndef _MobileAsset_H_
#define _MobileAsset_H_

#import <Foundation/Foundation.h>

extern NSString *const ASAttributeDownloadSize;
extern NSString *const ASAttributeUnarchivedSize;
#include <stdbool.h>
#include <stdint.h>

#import <MobileAsset/MAProgressHandler.h>
#import <MobileAsset/MAAsset.h>
#import <MobileAsset/MAAssetQuery.h>
#import <MobileAsset/ASAsset.h>
#import <MobileAsset/ASAssetQuery.h>
#import <MobileAsset/MAXpcManager.h>
#import <MobileAsset/MAAbsoluteAssetId.h>
#import <MobileAsset/MADownloadOptions.h>
#import <MobileAsset/MAMsuDownloadOptions.h>
#import <MobileAsset/MADownloadConfig.h>
#import <MobileAsset/MAProgressNotification.h>
#import <MobileAsset/MAXpcConnection.h>

void* ASEnsureDataVault(void);
void* ASNonUserInitiatedDownloadsAllowed(void);
void* ASServerURLForAssetType(void);
void* ASSetAssetServerURL(void);
void* ASSetAssetServerURLForAssetType(void);
void* ASSetDefaultAssetServerURLForAssetType(void);
void* ASSetLogLevel(void);
void* MACleanV1Repository(void);
NSString* MAGetPallasAudience(NSString* assetType);
int64_t MAGetPallasEnabled(NSString* assetType, bool* enabled);
int64_t _MAsendGetPallasEnabled(NSString* assetType, bool* enabled);
int64_t MASetPallasEnabled(NSString* assetType, BOOL enabled);
int64_t _MAsendSetPallasEnabled(NSString* assetType, bool enabled);
int64_t MASetPallasAudienceForType(NSString* audience, NSString* assetType);
int64_t MASetPallasUrlForType(NSURL* url, NSString* assetType);
int64_t _MAsendSetPallasUrlForType(NSURL* url, NSString* assetType);
void* MAMigrateAssets(void);
void* MAPurgeAll(void);
void* MASendRepairState(void);
int64_t MASetPallasAudience(NSString* audience);
int64_t MASetPallasUrl(NSURL* url);
void* MASetServerUrlOverride(void);
void* MobileAssetQueryCreate(void);
void* MobileAssetQueryCreateArrayOfKnownAssets(void);
void* MobileAssetQueryGetMatchingAsset(void);
void* MobileAssetQueryGetTypeID(void);
void* MobileAssetQueryRefreshAssetsAgainstLocalCache(void);
void* MobileAssetQueryRefreshKnownAssets(void);
void* _ForceMetadataUpdate(void);
void* _MACleanV1Repository(void);
void* _MAClientSendRepairState(void);
void* _MAMigrateAssets(void);
void* _MAclientSendCoverageDump(void);
void* _MAclientSendQueryNSUrlState(void);
void* _MAclientSendRepairStateSync(void);
void* _MAclientSendServerUrlOverride(void);
void* _MAensureExtension(void);
void* _MAsendCancelDownload(void);
void* _MAsendConfigDownload(void);
void* _MAsendDownloadAsset(void);
void* _MAsendDownloadMetaData(void);
void* _MAsendDumpClientAccess(void);
void* _MAsendGarbageCollect(void);
NSString* _MAsendGetPallasAudience(NSString* assetType);
void* _MAsendPurgeAsset(void);
void* _MAsendQueryMetaData(void);
int64_t _MAsendSetPallasAudience(NSString* audience, NSString* assetType);
int64_t _MAsendSetPallasUrl(NSURL* url);
void* _MAsendUpdateClientAccess(void);
void* _MobileAssetGarbageCollectionBehaviorForAttributes(void);
void* _MobileAssetLog(void);
void* __DiscardDownloadQueueToken(void);
void* __ForceMigration(void);
void* __RetryQueuedDownloads(void);
void* __StartBackgroundedDownloads(void);
void* __TriggerAssetMigration(void);
void* _getClientCallbackQueue(void);
void* addObjectToMessage(void);

#endif
