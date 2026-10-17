#import <Foundation/Foundation.h>
#include <MobileGestalt/MobileGestalt.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
extern CFDictionaryRef _CFCopySupplementalVersionDictionary(void);
#define CHECK(c) do{if(!(c)){fprintf(stderr,"MG_ACTUAL_VERSION_FAIL %d %s\n",__LINE__,#c);abort();}}while(0)
int main(void){setbuf(stdout,NULL);@autoreleasepool{
 Dl_info owner;CHECK(dladdr((void *)MobileGestalt_copy_humanReadableProductVersionString_obj,&owner)&&strstr(owner.dli_fname,"/runtime/mobilegestalt-source/"));
 NSDictionary *disk=[NSDictionary dictionaryWithContentsOfFile:@"/System/Library/CoreServices/SystemVersion.plist"];NSString *version=[disk objectForKey:@"ProductVersion"];CHECK([version isKindOfClass:[NSString class]]);
 CFDictionaryRef supplement=_CFCopySupplementalVersionDictionary();id extra=supplement?(id)CFDictionaryGetValue(supplement,CFSTR("ProductVersionExtra")):nil;NSString *expected=extra?[NSString stringWithFormat:@"%@ %@",version,extra]:version;
 NSString *value=MobileGestalt_copy_humanReadableProductVersionString_obj();CHECK([value isEqualToString:expected]);
 CFStringRef named=MGCopyAnswer(CFSTR("ProductVersion"),NULL),hashed=MGCopyAnswer(CFSTR("qNNddlUK+B/YlooNoymwgA"),NULL);CHECK(named&&hashed&&CFEqual(named,(CFTypeRef)version)&&CFEqual(named,hashed));
 printf("SOURCE_MOBILEGESTALT_ACTUAL_GUEST_METADATA_AND_TYPED_OBJECT_OK %s\n",[value UTF8String]);CFRelease(named);CFRelease(hashed);if(supplement)CFRelease(supplement);return 0;
}}
