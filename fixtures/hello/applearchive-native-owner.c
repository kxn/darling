#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
int applearchive_native_owner(void) {
 const char *names[] = {"AAFileStreamOpenWithPath", "$s12AppleArchive0B10ByteStreamC010decryptionD011readingFrom17encryptionContext5flags11threadCountACSgAC_AA0b10EncryptionI0CAA0B5FlagsVSitFZ"};
 for (unsigned i = 0; i < 2; i++) {
  Dl_info owner = {0}; void *fn = dlsym(RTLD_DEFAULT, names[i]);
  if (!fn || !dladdr(fn, &owner) || !strstr(owner.dli_fname, "/runtime/applearchive-native/libraries/")) {
   fprintf(stderr,"NATIVE_ARCHIVE_WRONG_OWNER %s %s\n", names[i], owner.dli_fname ? owner.dli_fname : "<nil>"); return 0;
  }
  printf("NATIVE_ARCHIVE_OWNER_OK %s %s\n", names[i], owner.dli_fname);
 }
 return 1;
}
