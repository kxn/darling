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

#import <MobileAsset/MAAsset.h>

@implementation MAAsset {
    NSString* _assetType;
    NSString* _assetId;
    NSString* _purpose;
}
@synthesize attributes = _attributes, state = _state;
@synthesize assetType = _assetType, assetId = _assetId, purpose = _purpose;
- (instancetype)initWithAttributes:(NSDictionary*)record
{
    if (!(self = [super init])) return nil;
    if (![record isKindOfClass:[NSDictionary class]]) { [self release]; return nil; }
    id properties = [record objectForKey:@"AssetProperties"];
    id added = [record objectForKey:@"AssetAddedProperties"];
    if (![properties isKindOfClass:[NSDictionary class]] ||
        (added && ![added isKindOfClass:[NSDictionary class]])) { [self release]; return nil; }
    _attributes = [properties copy];
    _purpose = [[properties objectForKey:@"AssetPurpose"] copy];
    _state = [[added objectForKey:@"AssetState"] integerValue];
    _assetType = [[added objectForKey:@"AssetType"] copy];
    _assetId = [[added objectForKey:@"AssetId"] copy];
    return self;
}
- (void)dealloc
{
    [_attributes release]; [_assetType release]; [_assetId release]; [_purpose release];
    [super dealloc];
}
@end
