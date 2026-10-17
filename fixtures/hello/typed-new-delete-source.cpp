#include <new>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
namespace std { enum class __type_descriptor_t : unsigned long long; }
void* operator new(std::size_t,std::__type_descriptor_t);
void* operator new[](std::size_t,std::__type_descriptor_t);
void operator delete(void*,std::__type_descriptor_t) noexcept;
void operator delete[](void*,std::__type_descriptor_t) noexcept;
static unsigned checks;
#define CHECK(x) do { ++checks; if(!(x)){std::fprintf(stderr,"FAIL %d %s\n",__LINE__,#x);std::exit(1);} }while(0)
struct HandlerMarker { unsigned value; };
static unsigned handlerCalls;
static void throwingHandler(){++handlerCalls;throw HandlerMarker{0x845f};}
static void clearingHandler(){++handlerCalls;std::set_new_handler(nullptr);}
#ifdef TEST_REPLACEMENTS
extern "C" {extern unsigned allocationCounts[4];extern std::size_t lastAllocationSize;extern bool failReplacement;}
#endif
int main(){
    auto typedNew=static_cast<void*(*)(std::size_t,std::__type_descriptor_t)>(&::operator new);
    auto typedArrayNew=static_cast<void*(*)(std::size_t,std::__type_descriptor_t)>(&::operator new[]);
    auto typedDelete=static_cast<void(*)(void*,std::__type_descriptor_t) noexcept>(&::operator delete);
    auto typedArrayDelete=static_cast<void(*)(void*,std::__type_descriptor_t) noexcept>(&::operator delete[]);
    #ifndef LINUXCODE_TYPED_NEW_EXPECTED_PROVIDER
    #define LINUXCODE_TYPED_NEW_EXPECTED_PROVIDER "typed-new-delete-source/"
    #endif
    Dl_info owner;CHECK(dladdr(reinterpret_cast<void*>(typedNew),&owner));CHECK(std::strstr(owner.dli_fname,LINUXCODE_TYPED_NEW_EXPECTED_PROVIDER));
    void *library=dlopen("/usr/lib/libc++.1.dylib",RTLD_LAZY|RTLD_LOCAL);CHECK(library);
    CHECK(dlsym(library,"_ZnwmSt19__type_descriptor_t")==reinterpret_cast<void*>(typedNew));
#ifdef TEST_REPLACEMENTS
    std::memset(allocationCounts,0,sizeof(unsigned)*4);
#endif
    const unsigned long long tags[]={0,1,0x123456789abcdef0ULL,~0ULL};
    const std::size_t sizes[]={0,1,7,16,17,31,64,255,4096,65536};
    for(auto tag:tags)for(auto size:sizes){
        auto descriptor=static_cast<std::__type_descriptor_t>(tag);
        unsigned char *p=static_cast<unsigned char*>(typedNew(size,descriptor));CHECK(p);CHECK(reinterpret_cast<std::uintptr_t>(p)%alignof(std::max_align_t)==0);
#ifdef TEST_REPLACEMENTS
        CHECK(lastAllocationSize==size);
#endif
        std::memset(p,0x37,size?size:1);CHECK(p[0]==0x37);CHECK(p[(size?size:1)-1]==0x37);typedDelete(p,descriptor);
        p=static_cast<unsigned char*>(typedArrayNew(size,descriptor));CHECK(p);
#ifdef TEST_REPLACEMENTS
        CHECK(lastAllocationSize==size);
#endif
        std::memset(p,0xc8,size?size:1);CHECK(p[(size?size:1)-1]==0xc8);typedArrayDelete(p,descriptor);
    }
    auto tag=static_cast<std::__type_descriptor_t>(0x8000000000000001ULL);
#ifdef TEST_REPLACEMENTS
    std::printf("REPLACEMENT_COUNTS %u %u %u %u\n",allocationCounts[0],allocationCounts[1],allocationCounts[2],allocationCounts[3]);
    for(unsigned i=0;i<4;i++)CHECK(allocationCounts[i]==40);
    typedDelete(nullptr,tag);typedArrayDelete(nullptr,tag);CHECK(allocationCounts[2]==41);CHECK(allocationCounts[3]==41);
    failReplacement=true;unsigned caught=0;
    try{(void)typedNew(8,tag);}catch(const std::bad_alloc&){caught++;}
    try{(void)typedArrayNew(8,tag);}catch(const std::bad_alloc&){caught++;}
    CHECK(caught==2);failReplacement=false;
    std::printf("TYPED_CPP_REPLACEMENT_SCALAR_ARRAY_ZERO_NULL_AND_EXCEPTION_OK checks=%u\n",checks);
#else
    typedDelete(nullptr,tag);typedArrayDelete(nullptr,tag);
    // Both sides use the actual same legacy allocator.
    void *p=typedNew(32,tag);::operator delete(p);p=::operator new(32);typedDelete(p,tag);
    p=typedArrayNew(32,tag);::operator delete[](p);p=::operator new[](32);typedArrayDelete(p,tag);
    std::new_handler saved=std::set_new_handler(throwingHandler);unsigned caught=0;
    volatile std::size_t impossible=static_cast<std::size_t>(-1);
    try{(void)typedNew(impossible,tag);}catch(const HandlerMarker& e){CHECK(e.value==0x845f);caught++;}
    try{(void)typedArrayNew(impossible,tag);}catch(const HandlerMarker& e){CHECK(e.value==0x845f);caught++;}
    CHECK(handlerCalls==2);CHECK(caught==2);
    std::set_new_handler(nullptr);caught=0;
    try{(void)typedNew(impossible,tag);}catch(const std::bad_alloc&){caught++;}
    try{(void)typedArrayNew(impossible,tag);}catch(const std::bad_alloc&){caught++;}
    CHECK(caught==2);handlerCalls=0;caught=0;std::set_new_handler(clearingHandler);
    try{(void)typedNew(impossible,tag);}catch(const std::bad_alloc&){caught++;}
    CHECK(caught==1);CHECK(handlerCalls==1);std::set_new_handler(saved);
    std::printf("TYPED_CPP_REAL_ALLOCATOR_ALIGNMENT_NEW_HANDLER_BAD_ALLOC_AND_OWNERSHIP_OK checks=%u\n",checks);
#endif
}
