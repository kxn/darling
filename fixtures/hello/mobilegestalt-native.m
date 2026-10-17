#import <Foundation/Foundation.h>
#include <dlfcn.h>
#include <objc/runtime.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/sysctl.h>
#define CHECK(c) do{if(!(c)){fprintf(stderr,"NATIVE_MG_FAIL %d %s\n",__LINE__,#c);abort();}}while(0)
int main(int argc,char **argv){setbuf(stdout,NULL);@autoreleasepool{
 const char *path="/Volumes/SystemRoot/workspace/runtime/mobilegestalt-native/libraries/libMobileGestalt.dylib";
 void *h=dlopen(path,RTLD_LAZY|RTLD_LOCAL);if(!h){puts(dlerror());return 1;}
 const char *names[]={"MobileGestalt_copy_humanReadableProductVersionString_obj","MobileGestalt_copy_productType_obj","MobileGestalt_copy_runnableArchitectures_obj","MobileGestalt_copy_supplementalBuildVersion_obj","MobileGestalt_copy_uniqueDeviceID_obj","MobileGestalt_copy_userAssignedDeviceName_obj","MobileGestalt_get_cpuSubType","MobileGestalt_get_cpuType","MobileGestalt_get_current_device"};
 for(unsigned i=0;i<9;i++){void *fn=dlsym(h,names[i]);Dl_info owner;CHECK(fn&&dladdr(fn,&owner)&&!strcmp(owner.dli_fname,path));}
 puts("NATIVE_MOBILEGESTALT_ORIGINAL_NINE_ENTRIES_RESOLVED");
 if(argc>1&&!strcmp(argv[1],"load"))return 0;
 id (*get_device)(void)=dlsym(h,"MobileGestalt_get_current_device");id device=get_device();CHECK(device);printf("NATIVE_MOBILEGESTALT_CURRENT_DEVICE_CLASS %s\n",object_getClassName(device));CHECK(!strcmp(object_getClassName(device),"OS_MobileGestalt"));
 id (*copy_version)(id)=dlsym(h,"MobileGestalt_copy_humanReadableProductVersionString_obj");id version=copy_version(device);printf("NATIVE_MOBILEGESTALT_VERSION %s\n",version?[[version description]UTF8String]:"<nil>");CHECK([version isKindOfClass:[NSString class]]);
 if(argc>1&&!strcmp(argv[1],"version"))return 0;
 int (*cpu_type)(id)=dlsym(h,"MobileGestalt_get_cpuType"),(*cpu_subtype)(id)=dlsym(h,"MobileGestalt_get_cpuSubType");int type=cpu_type(device),subtype=cpu_subtype(device);printf("NATIVE_MOBILEGESTALT_CPU %d %d\n",type,subtype);
 int expected_type=0,expected_subtype=0;size_t size=sizeof(int);CHECK(!sysctlbyname("hw.cputype",&expected_type,&size,NULL,0));size=sizeof(int);CHECK(!sysctlbyname("hw.cpusubtype",&expected_subtype,&size,NULL,0));CHECK(type==expected_type&&subtype==expected_subtype);
 for(unsigned i=1;i<6;i++){id (*copy)(id)=dlsym(h,names[i]);printf("NATIVE_MOBILEGESTALT_QUERY_BEGIN %s\n",names[i]);id answer=copy(device);printf("NATIVE_MOBILEGESTALT_ANSWER %s class=%s present=%d\n",names[i],answer?object_getClassName(answer):"<nil>",answer!=nil);
  if(i==2){CHECK([answer isKindOfClass:[NSArray class]]);NSMutableArray *expected=[NSMutableArray array];void (*enumerate)(void (^)(const char *,bool *))=dlsym(RTLD_DEFAULT,"macho_for_each_runnable_arch_name");CHECK(enumerate);enumerate(^(const char *name,bool *stop){[expected addObject:[NSString stringWithUTF8String:name]];});CHECK([answer isEqualToArray:expected]);puts("NATIVE_MOBILEGESTALT_ARCHITECTURES_MATCH_REAL_DYLD_OK");if(argc>1&&!strcmp(argv[1],"architecture"))return 0;}}
 puts("NATIVE_MOBILEGESTALT_SELECTED_DEVICE_QUERIES_RETURNED");return 0;
}}
