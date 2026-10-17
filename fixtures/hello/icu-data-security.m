#import <Foundation/Foundation.h>
#import <Security/Security.h>
#include <CoreFoundation/CoreFoundation.h>
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
extern void u_getVersion(uint8_t version[4]);
static unsigned checks;
#define CHECK(x) do { if(!(x)){fprintf(stderr,"CHECK failed %d: %s\n",__LINE__,#x);return 3;}checks++;}while(0)
int main(int argc,char**argv) {
 setbuf(stdout,NULL);@autoreleasepool {
 uint8_t version[4];u_getVersion(version);printf("ICU_NATIVE_VERSION %u.%u.%u.%u\n",version[0],version[1],version[2],version[3]);CHECK(version[0]==78);
 CFNumberFormatterRef system=CFNumberFormatterCreate(NULL,CFLocaleGetSystem(),kCFNumberFormatterDecimalStyle);
 if(!system){puts("ICU_NATIVE_SYSTEM_NUMBER_FORMATTER_NULL");return 2;}CFRelease(system);
 const char* locales[]={"en_US_POSIX","en_US","de_DE","fr_FR"};
 int64_t values[]={0,1,42,73,1024,123456,-1,-42,2147483647};
 for(unsigned l=0;l<4;l++){
  CFStringRef identifier=CFStringCreateWithCString(NULL,locales[l],kCFStringEncodingUTF8);CFLocaleRef locale=CFLocaleCreate(NULL,identifier);
  CFNumberFormatterRef formatter=CFNumberFormatterCreate(NULL,locale,kCFNumberFormatterDecimalStyle);CHECK(formatter);
  for(unsigned i=0;i<9;i++){
   CFStringRef text=CFNumberFormatterCreateStringWithValue(NULL,formatter,kCFNumberSInt64Type,&values[i]);CHECK(text);
   CFRange range=CFRangeMake(0,CFStringGetLength(text));CFNumberRef parsed=CFNumberFormatterCreateNumberFromString(NULL,formatter,text,&range,kCFNumberFormatterParseIntegersOnly);CHECK(parsed);
   int64_t actual=0;CHECK(CFNumberGetValue(parsed,kCFNumberSInt64Type,&actual)&&actual==values[i]);CHECK(range.length==CFStringGetLength(text));CFRelease(parsed);CFRelease(text);
  }
  CFRelease(formatter);CFRelease(locale);CFRelease(identifier);
 }
 printf("ICU_ORIGINAL_NUMBER_FORMATTERS_FOUR_LOCALES_36_REAL_ROUNDTRIPS_OK checks=%u\n",checks);
 CHECK(argc==2);NSString* folder=[NSString stringWithUTF8String:argv[1]];
 NSData* der=[NSData dataWithContentsOfFile:[folder stringByAppendingPathComponent:@"public-key.der"]];
 NSData* message=[NSData dataWithContentsOfFile:[folder stringByAppendingPathComponent:@"message.bin"]];
 NSData* signature=[NSData dataWithContentsOfFile:[folder stringByAppendingPathComponent:@"signature.bin"]];CHECK(der&&message&&signature);
 CFErrorRef error=NULL;NSDictionary* attrs=@{(id)kSecAttrKeyType:(id)kSecAttrKeyTypeRSA,(id)kSecAttrKeyClass:(id)kSecAttrKeyClassPublic};
 puts("SECURITY_RSA_NATIVE_IMPORT_BEGIN");SecKeyRef key=SecKeyCreateWithData((CFDataRef)der,(CFDictionaryRef)attrs,&error);
 if(!key)fprintf(stderr,"RSA import error: %s\n",[[(__bridge NSError*)error description] UTF8String]);CHECK(key&&!error);CHECK(SecKeyGetBlockSize(key)==256);
 puts("SECURITY_RSA_NATIVE_IMPORT_OK");
 CHECK(SecKeyVerifySignature(key,kSecKeyAlgorithmRSASignatureMessagePKCS1v15SHA256,(CFDataRef)message,(CFDataRef)signature,&error));CHECK(!error);
 NSMutableData* changed=[message mutableCopy];((uint8_t*)changed.mutableBytes)[0]^=1;
 CHECK(!SecKeyVerifySignature(key,kSecKeyAlgorithmRSASignatureMessagePKCS1v15SHA256,(CFDataRef)changed,(CFDataRef)signature,&error));CHECK(error);CFRelease(error);[changed release];CFRelease(key);
 printf("SECURITY_RSA_NATIVE_IMPORT_OPENSSL_SHA256_SIGNATURE_AND_TAMPER_REJECTION_OK checks=%u\n",checks);
 }return 0;
}
