// Minimal OSAnalytics boundary used by XCResultKit. Constant values were read
// from the signed Apple recovery cache. Report conversion is NOT implemented:
// return a real NSError through the observed dictionary error contract.
#import <Foundation/Foundation.h>
#include <errno.h>
#include <stdio.h>

NSString *OSATransformOptionSymbolicate = @"xform-trace";
NSString *OSATransformResultError = @"xform-error";
NSString *OSATransformResultReport = @"symbolicated_log";

@interface OSALegacyXform : NSObject
+ (NSDictionary *)transformURL:(NSURL *)url options:(NSDictionary *)options;
+ (NSDictionary *)transformURL:(NSURL *)url template:(id)template options:(NSDictionary *)options;
@end

@implementation OSALegacyXform
+ (NSDictionary *)transformURL:(NSURL *)url options:(NSDictionary *)options {
    return [self transformURL:url template:nil options:options];
}
+ (NSDictionary *)transformURL:(NSURL *)url template:(id)template options:(NSDictionary *)options {
    fputs("linuxcode: OSAnalytics legacy crash-report transformation is not implemented\n", stderr);
    NSMutableDictionary *info = [NSMutableDictionary dictionaryWithObject:
        @"OSAnalytics crash-report conversion and symbolication are not implemented in this Darling environment."
        forKey:NSLocalizedDescriptionKey];
    if (url) [info setObject:url forKey:NSURLErrorKey];
    NSError *error = [NSError errorWithDomain:NSPOSIXErrorDomain code:ENOTSUP userInfo:info];
    return [NSDictionary dictionaryWithObject:error forKey:OSATransformResultError];
}
@end
