#include <os/log.h>
#include <dlfcn.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
/* Intel layout read by the original copy routine, including its payload pool.
 * No Darling os_log_s object is cast to this native message record. */
struct native_message {uint8_t prefix[0x50];uint64_t flags;const char *format;const void *public_data;size_t public_size;const void *private_data;size_t private_size;};
_Static_assert(offsetof(struct native_message,format)==0x58,"native message format offset");
_Static_assert(sizeof(struct native_message)==0x80,"native message size");
static char *(*copy_message)(const struct native_message *);
#define CHECK(c) do{if(!(c)){fprintf(stderr,"NATIVE_LOG_MESSAGE_FAIL %d %s\n",__LINE__,#c);exit(1);}}while(0)
static void check(struct native_message *message,const char *expected){char *result=copy_message(message);printf("NATIVE_MESSAGE_RESULT %s\n",result?result:"<NULL>");CHECK(result&&strcmp(result,expected)==0);free(result);}
int main(int argc,char **argv){setbuf(stdout,NULL);
 void *provider=dlopen("/usr/lib/libDarlingMetrics.dylib",RTLD_LAZY|RTLD_LOCAL);if(!provider){puts(dlerror());return 1;}copy_message=dlsym(provider,"os_log_copy_message_string");CHECK(copy_message);Dl_info owner;CHECK(dladdr((void *)copy_message,&owner));printf("NATIVE_MESSAGE_PROVIDER %s\n",owner.dli_fname);CHECK(strstr(owner.dli_fname,"libDarlingMetrics.dylib"));
 struct native_message message={.format="literal 100% untouched"};check(&message,"literal 100% untouched");
 if(argc>1){void *native=(void *)copy_message;copy_message=dlsym(RTLD_DEFAULT,"os_log_copy_message_string");CHECK(copy_message&&(void *)copy_message!=native);CHECK(dladdr((void *)copy_message,&owner)&&strstr(owner.dli_fname,"libDarlingLogMessage.dylib"));puts("LIBSYSTEM_MESSAGE_IMPORT_USES_VERIFIED_FORWARDER");check(&message,"literal 100% untouched");}
 unsigned n=__builtin_os_log_format_buffer_size("integer=%{public}d",-77);uint8_t scalar[n];__builtin_os_log_format(scalar,"integer=%{public}d",-77);
 message.format="integer=%{public}d";message.public_data=scalar;message.public_size=n;check(&message,"integer=-77");
 unsigned n2=__builtin_os_log_format_buffer_size("%{public}llu %{public}.2f",UINT64_MAX,1.25);uint8_t scalars[n2];__builtin_os_log_format(scalars,"%{public}llu %{public}.2f",UINT64_MAX,1.25);
 message.format="%{public}llu %{public}.2f";message.public_data=scalars;message.public_size=n2;check(&message,"18446744073709551615 1.25");
 // Serialized string descriptors use a 16-bit pool offset and length rather
 // than the process-local pointer emitted before the log transport packs it.
 uint8_t string[]={2,1,0x22,4,0,0,6,0,'h','e','l','l','o',0};
 message.format="text=%{public}s";message.public_data=string;message.public_size=sizeof(string);check(&message,"text=hello");
 uint8_t private_string[]={1,1,0x21,4,0,0,7,0};message.format="hidden=%{private}s";message.public_data=private_string;message.public_size=sizeof(private_string);message.private_data="secret";message.private_size=7;message.flags=1;check(&message,"hidden=secret");
 message.flags=0;check(&message,"hidden=secret");
 message.private_data=NULL;message.private_size=0;check(&message,"hidden=<private>");
 puts("ORIGINAL_LOG_MESSAGE_LITERAL_PUBLIC_SCALARS_AND_SERIALIZED_STRING_OK");dlclose(provider);return 0;
}
