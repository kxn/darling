#include <CoreFoundation/CoreFoundation.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include "native-crypto-constants.inc"
int main(void) {
 setbuf(stdout,NULL);
 const char *frameworks[]={"/System/Library/Frameworks/Security.framework/Versions/A/Security","/System/Library/Frameworks/CryptoTokenKit.framework/Versions/A/CryptoTokenKit","/System/Library/Frameworks/LocalAuthentication.framework/Versions/A/LocalAuthentication"};
 for(unsigned i=0;i<3;i++)assert(dlopen(frameworks[i],RTLD_LAZY|RTLD_GLOBAL));
 for(unsigned i=0;i<sizeof(constants)/sizeof(constants[0]);i++) {
  CFStringRef *value=dlsym(RTLD_DEFAULT,constants[i].name+1);assert(value&&*value);
  assert(CFGetTypeID(*value)==CFStringGetTypeID());char buffer[256];
  assert(CFStringGetCString(*value,buffer,sizeof(buffer),kCFStringEncodingUTF8));assert(!strcmp(buffer,constants[i].value));
  assert(CFStringGetLength(*value)==strlen(buffer));CFStringRef copy=CFStringCreateCopy(NULL,*value);assert(copy&&CFEqual(copy,*value));CFRelease(copy);
  printf("NATIVE_CRYPTO_CONSTANT_OK %s %s\n",constants[i].name,buffer);
 }
 printf("NATIVE_CRYPTO_CONSTANT_TYPES_VALUES_COPY_OK checks=%zu\n",sizeof(constants)/sizeof(constants[0]));return 0;
}
