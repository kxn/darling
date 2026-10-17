#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
int cryptokit_original_owner(void) {
 const char *names[]={"ccsha256_di","$s9CryptoKit6SHA256VMa","OBJC_CLASS_$_TKClientTokenSession"};
 const char *paths[]={"/runtime/rebuilt-corecrypto-original-native-v2/","/runtime/cryptokit-original-native/frameworks/","/runtime/crypto-token-kit-native/frameworks/"};
 for(unsigned i=0;i<3;i++){Dl_info info={0};void *p=dlsym(RTLD_DEFAULT,names[i]);if(!p||!dladdr(p,&info)||!strstr(info.dli_fname,paths[i])){fprintf(stderr,"ORIGINAL_CRYPTO_WRONG_OWNER %s %s\n",names[i],info.dli_fname?info.dli_fname:"nil");return 0;}printf("ORIGINAL_CRYPTO_OWNER %s %s\n",names[i],info.dli_fname);}
 return 1;
}
