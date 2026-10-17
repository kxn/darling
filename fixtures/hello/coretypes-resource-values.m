#import <Foundation/Foundation.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
int main(int argc,char **argv) {
    setbuf(stdout,NULL);
    @autoreleasepool {
        if(argc>1 && !strcmp(argv[1],"--wait")) {
            printf("CORETYPES_METADATA_READY %d\n",getpid());
            FILE *gate=fopen("/Volumes/SystemRoot/workspace/runtime/coretypes-debug-release","r");
            if(!gate)return 2;fgetc(gate);fclose(gate);
        }
        NSString *path=@"/System/Library/CoreServices/CoreTypes.bundle";
        NSURL *url=[NSURL fileURLWithPath:path isDirectory:YES];
        NSError *error=nil; id value=nil;
        BOOL ok=[url getResourceValue:&value forKey:NSURLIsDirectoryKey error:&error];
        printf("CORETYPES_URL_IS_DIRECTORY ok=%d value=%s error=%s\n",ok,[[value description] UTF8String],[[error description] UTF8String]);
        error=nil;NSDictionary *attrs=[[NSFileManager defaultManager] attributesOfItemAtPath:path error:&error];
        printf("CORETYPES_FILEMANAGER_ATTRIBUTES count=%lu error=%s\n",(unsigned long)[attrs count],[[error description] UTF8String]);
        __block BOOL enumerationError=NO;
        NSDirectoryEnumerator *enumerator=[[NSFileManager defaultManager] enumeratorAtURL:url includingPropertiesForKeys:@[NSURLNameKey,NSURLIsDirectoryKey,NSURLIsRegularFileKey,NSURLFileSizeKey] options:0 errorHandler:^BOOL(NSURL *entry,NSError *failure) {
            enumerationError=YES;printf("CORETYPES_ENUMERATION_ERROR %s\n",[[failure description] UTF8String]);return NO;
        }];
        printf("CORETYPES_ENUMERATOR_CLASS %s\n",[NSStringFromClass([enumerator class]) UTF8String]);
        unsigned count=0;for(NSURL *entry in enumerator) {printf("CORETYPES_ENUMERATED %s\n",[[entry path] UTF8String]);if(++count==3)break;}
        if(!count) {
            NSURL *next=[enumerator nextObject];
            printf("CORETYPES_ENUMERATOR_NEXT %s\n",[[next path] UTF8String]);
            NSError *listingError=nil;
            NSArray *listing=[[NSFileManager defaultManager] contentsOfDirectoryAtPath:path error:&listingError];
            printf("CORETYPES_DIRECTORY_LISTING count=%lu error=%s\n",(unsigned long)[listing count],[[listingError description] UTF8String]);
        }
        printf("CORETYPES_METADATA_RESULT directory=%d attributes=%d enumeration=%u errors=%d\n",ok&&[value boolValue],attrs!=nil,count,enumerationError);
        return !(ok&&[value boolValue]&&attrs&&count&&!enumerationError);
    }
}
