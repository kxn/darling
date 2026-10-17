#include <CoreFoundation/CoreFoundation.h>
#include <dlfcn.h>
#include <stdbool.h>
#include <assert.h>
#include <stdio.h>

int main(int argc,char **argv) {
    if(argc!=2)return 2;
    void *image=dlopen(argv[1],RTLD_LAZY|RTLD_LOCAL);
    if(!image){fprintf(stderr,"%s\n",dlerror());return 1;}
    bool (*contains)(CFStringRef)=dlsym(image,"CEMStringContainsEmoji");
    assert(contains);
    assert(!contains(NULL) && !contains(CFSTR("plain ASCII text")));
    assert(contains(CFSTR("\U0001F600")));
    assert(contains(CFSTR("hello \U0001F600 world")));
    puts("ORIGINAL_CORE_EMOJI_ASCII_NEGATIVE_EMOJI_POSITIVE_OK");
}
