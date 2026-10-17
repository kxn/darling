#include <xpc/xpc.h>
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(c) do{checks++;if(!(c)){fprintf(stderr,"XPC_EMPTY_ARRAY_FAIL %d %s\n",__LINE__,#c);abort();}}while(0)
int main(void){setbuf(stdout,NULL);
    Dl_info owner;CHECK(dladdr((void*)xpc_array_create_empty,&owner));CHECK(strstr(owner.dli_fname,"libxpc.dylib"));
    xpc_object_t a=xpc_array_create_empty(),b=xpc_array_create_empty();CHECK(a&&b&&a!=b);
    CHECK(xpc_get_type(a)==XPC_TYPE_ARRAY&&xpc_array_get_count(a)==0&&xpc_array_get_count(b)==0);
    xpc_object_t text=xpc_string_create("你好 Linux");xpc_array_append_value(a,text);xpc_release(text);
    xpc_array_set_int64(a,XPC_ARRAY_APPEND,INT64_MIN);xpc_array_set_bool(a,XPC_ARRAY_APPEND,false);
    const uint8_t bytes[]={0,1,0,255,0,73};xpc_array_set_data(a,XPC_ARRAY_APPEND,bytes,sizeof(bytes));
    CHECK(xpc_array_get_count(a)==4&&xpc_array_get_count(b)==0);
    CHECK(!strcmp(xpc_array_get_string(a,0),"你好 Linux"));CHECK(xpc_array_get_int64(a,1)==INT64_MIN);CHECK(!xpc_array_get_bool(a,2));
    size_t size=0;const void *data=xpc_array_get_data(a,3,&size);CHECK(size==sizeof(bytes)&&!memcmp(data,bytes,size));
    xpc_array_set_string(a,0,"replacement");CHECK(!strcmp(xpc_array_get_string(a,0),"replacement")&&xpc_array_get_count(a)==4);
    for(unsigned i=0;i<1024;i++)xpc_array_set_uint64(b,XPC_ARRAY_APPEND,UINT64_MAX-i);
    CHECK(xpc_array_get_count(b)==1024);
    for(unsigned i=0;i<1024;i++)CHECK(xpc_array_get_uint64(b,i)==UINT64_MAX-i);
    __block unsigned visited=0;CHECK(xpc_array_apply(b,^bool(size_t index,xpc_object_t value){visited++;return index==visited-1&&xpc_uint64_get_value(value)==UINT64_MAX-index;}));CHECK(visited==1024);
    visited=0;CHECK(!xpc_array_apply(b,^bool(size_t index,xpc_object_t value){visited++;return index<2;}));CHECK(visited==3);
    xpc_array_append_value(a,b);xpc_release(b);b=xpc_array_get_value(a,4);CHECK(xpc_get_type(b)==XPC_TYPE_ARRAY&&xpc_array_get_count(b)==1024);CHECK(xpc_array_get_uint64(b,1023)==UINT64_MAX-1023);
    xpc_release(a);printf("SOURCE_XPC_EMPTY_ARRAY_REAL_MUTATION_GROWTH_RETAIN_AND_APPLY_OK checks=%u\n",checks);return 0;
}
