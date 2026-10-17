// Type IDs carry allocation metadata. Preserve the existing allocator's
// allocation/throw behavior when Darling has no typed-allocation runtime.
using allocation_size = __SIZE_TYPE__;
extern "C" void *legacy_malloc(allocation_size) __asm__("_malloc");
extern "C" void *legacy_realloc(void *, allocation_size) __asm__("_realloc");
extern "C" void *legacy_calloc(allocation_size, allocation_size) __asm__("_calloc");
extern "C" void *malloc_type_malloc(allocation_size size, unsigned long long) {
    return legacy_malloc(size);
}
extern "C" void *malloc_type_realloc(void *pointer, allocation_size size, unsigned long long) {
    return legacy_realloc(pointer,size);
}
extern "C" void *malloc_type_calloc(allocation_size count, allocation_size size, unsigned long long) {
    return legacy_calloc(count,size);
}
namespace std { enum class __type_descriptor_t : unsigned long long; }
void *operator new(allocation_size);
void *operator new[](allocation_size);
void operator delete(void *) noexcept;
void operator delete[](void *) noexcept;
void *operator new(allocation_size size, std::__type_descriptor_t) {
    return ::operator new(size);
}
void *operator new[](allocation_size size, std::__type_descriptor_t) {
    return ::operator new[](size);
}
void operator delete(void *pointer, std::__type_descriptor_t) noexcept {
    ::operator delete(pointer);
}
void operator delete[](void *pointer, std::__type_descriptor_t) noexcept {
    ::operator delete[](pointer);
}
