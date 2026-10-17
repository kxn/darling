#include <new>
#include <cstddef>
#include <cstdlib>
extern "C" {
unsigned allocationCounts[4];std::size_t lastAllocationSize;bool failReplacement;
}
void* operator new(std::size_t size){++allocationCounts[0];lastAllocationSize=size;if(failReplacement)throw std::bad_alloc();void *p=std::malloc(size?size:1);if(!p)throw std::bad_alloc();return p;}
void* operator new[](std::size_t size){++allocationCounts[1];lastAllocationSize=size;if(failReplacement)throw std::bad_alloc();void *p=std::malloc(size?size:1);if(!p)throw std::bad_alloc();return p;}
void operator delete(void* p) noexcept{++allocationCounts[2];std::free(p);}
void operator delete[](void* p) noexcept{++allocationCounts[3];std::free(p);}
