#include <assert.h>
#include <cpuid.h>
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef uint64_t (*Fletcher)(const void *,size_t,uint64_t);
static uint64_t reference(const uint32_t *words,size_t count,uint64_t seed) {
    const uint64_t modulus=UINT64_C(0xffffffff);
    uint64_t first=(uint32_t)seed,second=seed>>32;
    for (size_t index=0;index<count;++index) {
        first=(first+words[index])%modulus;
        second=(second+first)%modulus;
    }
    return ((second%modulus)<<32)|(first%modulus);
}
static unsigned vector_level(void) {
    unsigned a,b,c,d;
    if (!__get_cpuid(1,&a,&b,&c,&d) || !(c&bit_AVX) || !(c&bit_OSXSAVE)) return 0;
    unsigned low,high;
    __asm__ volatile("xgetbv":"=a"(low),"=d"(high):"c"(0));
    if ((low&6)!=6) return 0;
    return __get_cpuid_count(7,0,&a,&b,&c,&d) && (b&bit_AVX2) ? 2 : 1;
}
int main(int argc,char **argv) {
    if (argc!=5) return 2;
    void *image=dlopen(argv[1],RTLD_LAZY|RTLD_LOCAL);
    if (!image) { fprintf(stderr,"%s\n",dlerror());return 1; }
    void *anchor=dlsym(image,"APFSVolumeRole");Dl_info owner;
    assert(anchor && dladdr(anchor,&owner) && owner.dli_fbase);
    Fletcher functions[3];
    for (unsigned index=0;index<3;++index)
        functions[index]=(Fletcher)((char *)owner.dli_fbase+strtoull(argv[index+2],NULL,0));
    void *allocation=NULL;assert(posix_memalign(&allocation,32,4096*4+32)==0);
    uint32_t *storage=allocation;uint32_t random=0x12345678;
    for (unsigned index=0;index<4096+8;++index) {
        random=random*1664525+1013904223;
        storage[index]=(index%5==0)?UINT32_MAX:random;
    }
    const unsigned lengths[]={0,1,2,3,4,7,8,9,15,16,17,63,64,65,257,1024,4096};
    const uint64_t seeds[]={0,UINT64_MAX,UINT64_C(0x0123456789abcdef),UINT64_C(0x8765432101234567)};
    unsigned variants=vector_level()+1,checks=0;
    for (unsigned variant=0;variant<variants;++variant)
        for (unsigned shift=0;shift<3;++shift)
            for (unsigned length=0;length<sizeof(lengths)/sizeof(lengths[0]);++length)
                for (unsigned seed=0;seed<sizeof(seeds)/sizeof(seeds[0]);++seed) {
                    const uint32_t *input=storage+shift;
                    uint64_t expected=reference(input,lengths[length],seeds[seed]);
                    uint64_t actual=functions[variant](input,lengths[length]*4,seeds[seed]);
                    if (actual!=expected) {
                        fprintf(stderr,"Fletcher mismatch variant=%u length=%u shift=%u seed=%u expected=%llx actual=%llx\n",
                            variant,lengths[length],shift,seed,(unsigned long long)expected,(unsigned long long)actual);
                        return 1;
                    }
                    ++checks;
                }
    free(allocation);
    printf("Original Fletcher variants=%u checks=%u\n",variants,checks);
    puts("ORIGINAL_APFS_FLETCHER_SIMD_AGREES_WITH_SCALAR_MODULAR_REFERENCE_OK");
    return 0;
}
