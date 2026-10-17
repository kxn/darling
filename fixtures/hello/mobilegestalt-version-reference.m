#import <Foundation/Foundation.h>
#include <MobileGestalt/MobileGestalt.h>
#include <pthread.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
static CFDictionaryRef system_input,supplemental_input;
static bool mz;
static unsigned checks,cases;
#define CHECK(c) do{__sync_fetch_and_add(&checks,1);if(!(c)){fprintf(stderr,"MG_VERSION_FAIL %d %s\n",__LINE__,#c);abort();}}while(0)
CFStringRef reference_product_key=CFSTR("ProductVersion");
const CFStringRef *reference_product_key_address=&reference_product_key;
CFStringRef reference_ios_key=CFSTR("iOSSupportVersion");
CFStringRef reference_product_question=CFSTR("qNNddlUK+B/YlooNoymwgA");
CFStringRef reference_extra_key=CFSTR("ProductVersionExtra");
CFStringRef reference_format=CFSTR("%@ %@");
const CFAllocatorRef *reference_allocator_address=&kCFAllocatorDefault;
extern CFTypeRef reference_product_version(void);
extern CFStringRef reference_human_version(void);
/* These factories are controlled test inputs. Real CoreFoundation continues
 * to perform every retain, dictionary lookup and formatting operation. */
CFDictionaryRef _CFCopySystemVersionDictionary(void){return system_input?(CFDictionaryRef)CFRetain(system_input):NULL;}
CFDictionaryRef _CFCopySupplementalVersionDictionary(void){return supplemental_input?(CFDictionaryRef)CFRetain(supplemental_input):NULL;}
bool _CFMZEnabled(void){return mz;}
CFTypeRef reference_copy_system_value(CFStringRef key,int flag){CHECK(flag==1);CFTypeRef v=system_input?CFDictionaryGetValue(system_input,key):NULL;return v?CFRetain(v):NULL;}
CFStringRef reference_cached_product(CFStringRef question,void *error){CHECK(CFEqual(question,reference_product_question));CHECK(!error);CFTypeRef v=reference_product_version();if(v&&CFGetTypeID(v)!=CFStringGetTypeID()){CFRelease(v);return NULL;}return (CFStringRef)v;}
CFTypeRef reference_copy_value_and_release_dictionary(CFDictionaryRef d,CFStringRef key,int flag){CHECK(flag==1&&CFEqual(key,reference_extra_key));CFTypeRef v=d?CFDictionaryGetValue(d,key):NULL;if(v)CFRetain(v);if(d)CFRelease(d);return v;}
static void inputs(CFTypeRef version,CFTypeRef extra,bool catalyst){
 if(system_input)CFRelease(system_input);if(supplemental_input)CFRelease(supplemental_input);
 CFMutableDictionaryRef s=CFDictionaryCreateMutable(NULL,0,&kCFTypeDictionaryKeyCallBacks,&kCFTypeDictionaryValueCallBacks);
 if(version)CFDictionarySetValue(s,CFSTR("ProductVersion"),version);
 CFDictionarySetValue(s,CFSTR("iOSSupportVersion"),CFSTR("14.7"));
 CFDictionarySetValue(s,CFSTR("ProductUserVisibleVersion"),CFSTR("different-visible-version"));system_input=s;
 CFMutableDictionaryRef d=CFDictionaryCreateMutable(NULL,0,&kCFTypeDictionaryKeyCallBacks,&kCFTypeDictionaryValueCallBacks);
 CFDictionarySetValue(d,CFSTR("ProductVersion"),CFSTR("99.99"));if(extra)CFDictionarySetValue(d,reference_extra_key,extra);supplemental_input=d;mz=catalyst;
}
static void compare(void){@autoreleasepool{
 CFStringRef original=reference_human_version();id actual=MobileGestalt_copy_humanReadableProductVersionString_obj();
 CHECK((!original&&!actual)||(original&&actual&&CFEqual(original,(CFTypeRef)actual)));
 CFStringRef named=MGCopyAnswer(CFSTR("HumanReadableProductVersionString"),NULL),hashed=MGCopyAnswer(CFSTR("ToLFRidm+eJGWnpw6W4Wwg"),NULL);
 CHECK((!named&&!actual)||(named&&actual&&CFEqual(named,(CFTypeRef)actual)));CHECK((!hashed&&!actual)||(hashed&&actual&&CFEqual(hashed,(CFTypeRef)actual)));
 if(original)CFRelease(original);if(named)CFRelease(named);if(hashed)CFRelease(hashed);__sync_fetch_and_add(&cases,1);
}}
static void *worker(void *unused){for(unsigned i=0;i<32;i++)compare();return NULL;}
int main(void){setbuf(stdout,NULL);@autoreleasepool{
 inputs(CFSTR("26.2"),NULL,false);compare();
 inputs(CFSTR("26.2"),CFSTR("(a)"),false);compare();
 inputs(CFSTR("26.2"),CFSTR(""),false);compare();
 inputs(CFSTR("26.2β"),CFSTR("补充"),false);compare();
 int n=7;CFNumberRef number=CFNumberCreate(NULL,kCFNumberIntType,&n);inputs(CFSTR("26.2"),number,false);compare();CFRelease(number);
 inputs(NULL,CFSTR("(a)"),false);compare();
 inputs(CFSTR("26.2"),CFSTR("(b)"),true);compare();
 CFMutableStringRef mutable=CFStringCreateMutable(NULL,0);CFStringAppend(mutable,CFSTR("26.2 mutable-version-owned-input"));inputs(mutable,NULL,false);
 CFIndex before=CFGetRetainCount(mutable);NSAutoreleasePool *pool=[NSAutoreleasePool new];id borrowed=MobileGestalt_copy_humanReadableProductVersionString_obj();CHECK(borrowed==(id)mutable);CHECK(CFGetRetainCount(mutable)==before+1);[pool drain];CHECK(CFGetRetainCount(mutable)==before);CFRelease(mutable);compare();
 errno=0;CHECK(MGCopyAnswer(NULL,NULL)==NULL&&errno==EINVAL);errno=0;CHECK(MGCopyAnswer(CFSTR("not-a-supported-device-question"),NULL)==NULL&&errno==ENOTSUP);
 inputs(CFSTR("26.2"),CFSTR("(a)"),false);pthread_t threads[8];for(unsigned i=0;i<8;i++)CHECK(!pthread_create(&threads[i],NULL,worker,NULL));for(unsigned i=0;i<8;i++)CHECK(!pthread_join(threads[i],NULL));
 CFRelease(system_input);CFRelease(supplemental_input);printf("SOURCE_MOBILEGESTALT_ORIGINAL_CALLBACK_DIFFERENTIAL_AUTORELEASE_AND_CONCURRENCY_OK cases=%u checks=%u\n",cases,checks);return 0;
}}
