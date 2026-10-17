#include <dlfcn.h>
#include <new>
#include <cstdint>
#include <cassert>
#include <cstring>
#include <cstdio>

int main(int argc,char **argv) {
    if(argc!=2)return 2;
    void *image=dlopen(argv[1],RTLD_LAZY|RTLD_LOCAL);
    if(!image){std::fprintf(stderr,"%s\n",dlerror());return 1;}
    using Allocate=void *(*)(std::size_t,std::uint64_t);
    using Free=void (*)(void *,std::uint64_t);
    auto allocate=reinterpret_cast<Allocate>(dlsym(image,"_ZnwmSt19__type_descriptor_t"));
    auto array=reinterpret_cast<Allocate>(dlsym(image,"_ZnamSt19__type_descriptor_t"));
    auto release=reinterpret_cast<Free>(dlsym(image,"_ZdlPvSt19__type_descriptor_t"));
    auto releaseArray=reinterpret_cast<Free>(dlsym(image,"_ZdaPvSt19__type_descriptor_t"));
    assert(allocate && array && release && releaseArray);
    for(unsigned i=0;i<2;++i){
        void *p=(i?array:allocate)(96,123);assert(p);
        std::memset(p,0x5a,96);
        for(unsigned j=0;j<96;++j)assert(static_cast<unsigned char *>(p)[j]==0x5a);
        (i?releaseArray:release)(p,123);
    }
    release(nullptr,0);releaseArray(nullptr,0);
    bool failed=false;
    try { void *p=allocate(SIZE_MAX,0);release(p,0); }
    catch(const std::bad_alloc &){failed=true;}
    assert(failed);
    puts("TYPED_CXX_NEW_ARRAY_DELETE_AND_BAD_ALLOC_OK");
}
