#import <Foundation/Foundation.h>
#include <assert.h>
#include <errno.h>
#include <stdio.h>
extern NSString *OSATransformOptionSymbolicate;
extern NSString *OSATransformResultError;
extern NSString *OSATransformResultReport;
@interface OSALegacyXform : NSObject
+ (NSDictionary *)transformURL:(NSURL *)url options:(NSDictionary *)options;
@end
int main(void) {
    @autoreleasepool {
        assert([OSATransformOptionSymbolicate isEqualToString:@"xform-trace"]);
        assert([OSATransformResultError isEqualToString:@"xform-error"]);
        assert([OSATransformResultReport isEqualToString:@"symbolicated_log"]);
        NSURL *url = [NSURL fileURLWithPath:@"/tmp/not-an-implemented-crash-report"];
        NSDictionary *result = [OSALegacyXform transformURL:url options:[NSDictionary dictionary]];
        id error = [result objectForKey:OSATransformResultError];
        assert([error isKindOfClass:[NSError class]]);
        assert([error code] == ENOTSUP);
        assert([result objectForKey:OSATransformResultReport] == nil);
        puts("OSANALYTICS_CONSTANTS_OK_UNSUPPORTED_TRANSFORMATION_REJECTED");
    }
}
