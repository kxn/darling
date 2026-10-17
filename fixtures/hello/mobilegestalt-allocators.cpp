#include <dlfcn.h>
#include <malloc/malloc.h>
#include <new>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(c) do{if(!(c)){fprintf(stderr,"MG_ALLOCATOR_FAIL %d %s\n",__LINE__,#c);abort();}}while(0)
int main(){setbuf(stdout,nullptr);void *h=dlopen("/usr/lib/libDarlingDER.dylib",RTLD_LAZY|RTLD_LOCAL);CHECK(h);
 auto allocate=reinterpret_cast<void *(*)(size_t,uint64_t)>(dlsym(h,"_ZnwmSt19__type_descriptor_t"));auto dispose=reinterpret_cast<void (*)(void *,uint64_t)>(dlsym(h,"_ZdlPvSt19__type_descriptor_t"));CHECK(allocate&&dispose);
 Dl_info owner;CHECK(dladdr(reinterpret_cast<void *>(allocate),&owner)&&strstr(owner.dli_fname,"/runtime/rebuilt-der/"));CHECK(dladdr(reinterpret_cast<void *>(dispose),&owner)&&strstr(owner.dli_fname,"/runtime/rebuilt-der/"));
 const size_t sizes[]={0,1,7,32,257,4096,65537};unsigned allocations=0;
 for(unsigned i=0;i<64;i++)for(size_t n:sizes){auto *p=static_cast<unsigned char *>(allocate(n,UINT64_C(0xcafef00d01230000)+i));CHECK(p&&malloc_size(p)>=(n?n:1));if(n){memset(p,0x91,n);CHECK(p[0]==0x91&&p[n-1]==0x91);}dispose(p,UINT64_C(0xcafef00d01230000)+i);allocations++;}
 dispose(nullptr,0);auto previous=std::set_new_handler(nullptr);bool caught=false;try{void *p=allocate(SIZE_MAX,17);dispose(p,17);}catch(const std::bad_alloc &){caught=true;}std::set_new_handler(previous);CHECK(caught);
 printf("EXISTING_TYPED_CPP_ADAPTER_REAL_NEW_DELETE_AND_BAD_ALLOC_OK allocations=%u\n",allocations);return 0;
}
