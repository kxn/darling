#import <Foundation/Foundation.h>
#include <stdio.h>
#include <assert.h>
int main(int argc,char**argv){
 @autoreleasepool {
  assert(argc==2);NSDictionary* actual=[NSDictionary dictionaryWithContentsOfFile:@"/System/Library/CoreServices/SystemVersion.plist"];
  NSDictionary* expected=[NSDictionary dictionaryWithContentsOfFile:[NSString stringWithUTF8String:argv[1]]];
  assert(actual && expected && [actual isEqual:expected]);
  assert([actual[@"ProductBuildVersion"] isEqual:@"25G83"] && [actual[@"ProductVersion"] isEqual:@"26.6.2"]);
  printf("ORIGINAL_REFERENCE_SYSTEM_VERSION_VISIBLE_IN_PRIVATE_OVERLAY_OK version=%s build=%s\n",[actual[@"ProductVersion"] UTF8String],[actual[@"ProductBuildVersion"] UTF8String]);
 }return 0;
}
