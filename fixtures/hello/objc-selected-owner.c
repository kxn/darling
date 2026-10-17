#include <objc/runtime.h>
#include <mach-o/loader.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
int main(void){Dl_info owner;if(!dladdr((void*)sel_isMapped,&owner))return 1;printf("SELECTED_SEL_IS_MAPPED_OWNER %s\n",owner.dli_fname);if(!strstr(owner.dli_fname,"/runtime/objc-source/"))return 2;const struct mach_header_64 *h=owner.dli_fbase;if(h->magic!=MH_MAGIC_64)return 3;const char *p=(void*)(h+1);for(uint32_t i=0;i<h->ncmds;i++){const struct load_command *c=(void*)p;if(c->cmd==LC_UUID){printf("SELECTED_OBJC_UUID ");for(unsigned j=0;j<16;j++)printf("%02x",(unsigned char)p[8+j]);puts("");return 0;}p+=c->cmdsize;}return 4;}
