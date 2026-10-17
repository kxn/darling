#include <assert.h>
#include <dlfcn.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

int main(int argc,char **argv) {
    if (argc!=2)return 2;
    void *library=dlopen(argv[1],RTLD_LAZY|RTLD_LOCAL);
    if (!library){fprintf(stderr,"%s\n",dlerror());return 1;}
    void *(*create)(void)=dlsym(library,"mecab_lattice_new");
    void (*destroy)(void *)=dlsym(library,"mecab_lattice_destroy");
    void (*set_sentence)(void *,const char *)=dlsym(library,"mecab_lattice_set_sentence");
    const char *(*get_sentence)(void *)=dlsym(library,"mecab_lattice_get_sentence");
    size_t (*get_size)(void *)=dlsym(library,"mecab_lattice_get_size");
    void (*set_request)(void *,int)=dlsym(library,"mecab_lattice_set_request_type");
    int (*get_request)(void *)=dlsym(library,"mecab_lattice_get_request_type");
    int (*has_request)(void *,int)=dlsym(library,"mecab_lattice_has_request_type");
    assert(create && destroy && set_sentence && get_sentence && get_size && set_request && get_request && has_request);
    void *first=create(),*second=create();
    assert(first && second && first!=second);
    set_sentence(first,"Linux text");set_sentence(second,"second sentence");
    assert(get_size(first)==10 && strcmp(get_sentence(first),"Linux text")==0);
    assert(get_size(second)==15 && strcmp(get_sentence(second),"second sentence")==0);
    set_request(first,3);set_request(second,1);
    assert(get_request(first)==3 && has_request(first,2));
    assert(get_request(second)==1 && !has_request(second,2));
    set_sentence(first,"");assert(get_size(first)==0);
    assert(get_size(second)==15);
    destroy(first);destroy(second);
    puts("ORIGINAL_MECAB_TWO_LATTICES_SENTENCE_REQUEST_LIFECYCLE_OK");
}
