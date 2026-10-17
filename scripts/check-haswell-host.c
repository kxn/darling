// Run on the Linux host before a Darling runtime that reports x86_64h starts.
// Compile for baseline x86-64; XGETBV is reached only after OSXSAVE is present.
#include <cpuid.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

struct Feature { const char *name; unsigned group, bit; };
static const struct Feature required[] = {
    {"pclmul",1,1},{"ssse3",1,9},{"fma",1,12},{"cx16",1,13},
    {"sse4.1",1,19},{"sse4.2",1,20},{"movbe",1,22},{"popcnt",1,23},
    {"aes",1,25},{"xsave",1,26},{"osxsave",1,27},{"avx",1,28},
    {"f16c",1,29},{"rdrand",1,30},{"bmi1",2,3},{"avx2",2,5},
    {"bmi2",2,8},{"lahf_sahf",3,0},{"lzcnt",3,5}
};

int main(int argc,char **argv) {
    int json=argc==2 && !strcmp(argv[1],"--json");
    if (argc!=2 || (!json && strcmp(argv[1],"--require"))) return 2;
    unsigned a,b,c,d, groups[4]={0}, maximum=__get_cpuid_max(0,NULL);
    if (maximum>=1) { __cpuid_count(1,0,a,b,c,d);groups[1]=c; }
    if (maximum>=7) { __cpuid_count(7,0,a,b,c,d);groups[2]=b; }
    if (__get_cpuid_max(0x80000000,NULL)>=0x80000001) {
        __cpuid_count(0x80000001,0,a,b,c,d);groups[3]=c;
    }
    uint64_t xcr0=0;
    if ((groups[1] & ((1U<<26)|(1U<<27)))==((1U<<26)|(1U<<27))) {
        unsigned low,high;__asm__ volatile("xgetbv":"=a"(low),"=d"(high):"c"(0));
        xcr0=((uint64_t)high<<32)|low;
    }
    unsigned missing=0;
    for (unsigned i=0;i<sizeof(required)/sizeof(required[0]);++i)
        if (!(groups[required[i].group] & (1U<<required[i].bit))) ++missing;
    int ymm=(xcr0&6)==6, supported=!missing && ymm;
    if (json) {
        printf("{\"architecture\":\"x86_64\",\"haswell_isa_supported\":%s,\"xcr0\":\"0x%llx\",\"os_xmm_ymm_enabled\":%s,\"missing_features\":[",
               supported?"true":"false",(unsigned long long)xcr0,ymm?"true":"false");
        int comma=0;
        for (unsigned i=0;i<sizeof(required)/sizeof(required[0]);++i)
            if (!(groups[required[i].group] & (1U<<required[i].bit))) {
                printf("%s\"%s\"",comma?",":"",required[i].name);comma=1;
            }
        puts("]}");
    } else if (!supported) {
        fprintf(stderr,"This project runtime reports x86_64h; the current CPU/OS does not meet its guarded ISA requirements.\n");
    }
    return supported?0:1;
}
