#import <Foundation/Foundation.h>
#include <errno.h>

// Mappings and parameter ABI verified against the pinned original routines.
static NSInteger fileErrorCode(NSInteger code,BOOL reading) {
    if(reading) {
        switch(code) {
            case EPERM:case EACCES:return NSFileReadNoPermissionError;
            case ENOENT:return NSFileReadNoSuchFileError;
            case EFBIG:return NSFileReadTooLargeError;
            case ENAMETOOLONG:return NSFileReadInvalidFileNameError;
            default:return NSFileReadUnknownError;
        }
    }
    switch(code) {
        case EPERM:case EACCES:return NSFileWriteNoPermissionError;
        case ENOENT:return NSFileNoSuchFileError;
        case EEXIST:return NSFileWriteFileExistsError;
        case ENOSPC:case EDQUOT:return NSFileWriteOutOfSpaceError;
        case EROFS:return NSFileWriteVolumeReadOnlyError;
        case ENAMETOOLONG:return NSFileWriteInvalidFileNameError;
        default:return NSFileWriteUnknownError;
    }
}
NSError *_NSErrorWithFilePathErrnoVariantAndExtraUserInfo(NSInteger code,id path,BOOL reading,id variant,NSDictionary *extra) {
    NSMutableDictionary *info=[[NSMutableDictionary alloc] init];
    [info setObject:[NSError errorWithDomain:NSPOSIXErrorDomain code:code userInfo:nil] forKey:NSUnderlyingErrorKey];
    if(variant)[info setObject:[NSArray arrayWithObject:variant] forKey:@"NSUserStringVariant"];
    if(path)[info setObject:path forKey:[path isKindOfClass:[NSURL class]]?@"NSURL":NSFilePathErrorKey];
    for(id key in extra)if(![info objectForKey:key])[info setObject:[extra objectForKey:key] forKey:key];
    NSError *error=[NSError errorWithDomain:NSCocoaErrorDomain code:fileErrorCode(code,reading) userInfo:info];
    [info release];return error;
}
NSError *_NSErrorWithFilePathErrnoAndVariant(NSInteger code,id path,BOOL reading,id variant) {
    return _NSErrorWithFilePathErrnoVariantAndExtraUserInfo(code,path,reading,variant,nil);
}
