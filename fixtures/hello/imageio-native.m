#import <Foundation/Foundation.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#define CHECK(c) do{if(!(c)){fprintf(stderr,"NATIVE_IMAGEIO_FAIL line=%d %s\n",__LINE__,#c);abort();}}while(0)
int main(int argc,char **argv){setbuf(stdout,NULL);@autoreleasepool{
 const char *path="/Volumes/SystemRoot/workspace/runtime/imageio-legacy-key/frameworks/ImageIO.framework/Versions/A/ImageIO";
 void *h=dlopen(path,RTLD_LAZY|RTLD_LOCAL);if(!h){puts(dlerror());return 1;}
 const char *names[]={"CGImageSourceGetTypeID","CGImageSourceCreateWithData","CGImageSourceCreateWithURL","CGImageSourceCopyProperties","CGImageSourceCopyPropertiesAtIndex","CGImageSourceGetCount","CGImageSourceGetType"};
 for(unsigned i=0;i<7;i++){void *fn=dlsym(h,names[i]);Dl_info owner;CHECK(fn&&dladdr(fn,&owner)&&!strcmp(owner.dli_fname,path));}
 puts("NATIVE_IMAGEIO_ORIGINAL_SOURCE_PROPERTY_ENTRIES_LOADED");
 if(argc<2||(!strcmp(argv[1],"load")))return 0;
 NSData *analysisData=[NSData dataWithContentsOfFile:@"/Volumes/SystemRoot/workspace/artifacts/imageio-cg-constants-analysis.json"];CHECK(analysisData);NSDictionary *analysis=[NSJSONSerialization JSONObjectWithData:analysisData options:0 error:NULL];CHECK(analysis);
 NSDictionary *constants=analysis[@"constants"];unsigned checked=0;
 for(NSString *symbol in constants){const CFStringRef *value=dlsym(RTLD_DEFAULT,[[symbol substringFromIndex:1]UTF8String]);CHECK(value&&*value&&CFGetTypeID(*value)==CFStringGetTypeID());CHECK(CFEqual(*value,(CFStringRef)constants[symbol][@"value"]));checked++;}
 printf("NATIVE_IMAGEIO_CG_CONSTANTS_REAL_CFSTRING_VALUES_OK %u\n",checked);CHECK(checked==34);
 const float *matrix=dlsym(RTLD_DEFAULT,"matrix_identity_float3x3");CHECK(matrix&&((uintptr_t)matrix%16)==0);const float identity[12]={1,0,0,0,0,1,0,0,0,0,1,0};CHECK(!memcmp(matrix,identity,sizeof(identity)));puts("NATIVE_IMAGEIO_SOURCE_SIMD_MATRIX_LAYOUT_OK");
 CFTypeID (*getTypeID)(void)=dlsym(h,"CGImageSourceGetTypeID");CFTypeRef (*fromData)(CFDataRef,CFDictionaryRef)=dlsym(h,"CGImageSourceCreateWithData");CFTypeRef (*fromURL)(CFURLRef,CFDictionaryRef)=dlsym(h,"CGImageSourceCreateWithURL");CFDictionaryRef (*properties)(CFTypeRef,CFDictionaryRef)=dlsym(h,"CGImageSourceCopyProperties");CFDictionaryRef (*atIndex)(CFTypeRef,size_t,CFDictionaryRef)=dlsym(h,"CGImageSourceCopyPropertiesAtIndex");size_t (*count)(CFTypeRef)=dlsym(h,"CGImageSourceGetCount");CFStringRef (*type)(CFTypeRef)=dlsym(h,"CGImageSourceGetType");
 NSData *fixtureData=[NSData dataWithContentsOfFile:@"/Volumes/SystemRoot/workspace/artifacts/imageio-input-fixtures.json"];CHECK(fixtureData);NSArray *fixtures=[NSJSONSerialization JSONObjectWithData:fixtureData options:0 error:NULL];CHECK([fixtures count]==3);unsigned cases=0;
 for(NSDictionary *fixture in fixtures){NSString *file=[@"/Volumes/SystemRoot/workspace/" stringByAppendingString:fixture[@"path"]];NSData *data=[NSData dataWithContentsOfFile:file];CHECK(data&&[data length]==[fixture[@"bytes"]unsignedLongLongValue]);
  for(unsigned url=0;url<2;url++){printf("NATIVE_IMAGEIO_PARSE_BEGIN %s url=%u\n",[[file lastPathComponent]UTF8String],url);CFTypeRef source=url?fromURL((CFURLRef)[NSURL fileURLWithPath:file],NULL):fromData((CFDataRef)data,NULL);CHECK(source);CHECK(CFGetTypeID(source)==getTypeID());CHECK(count(source)==1);CHECK(CFEqual(type(source),(CFStringRef)fixture[@"uti"]));
   CFDictionaryRef global=properties(source,NULL);CHECK(global&&CFGetTypeID(global)==CFDictionaryGetTypeID());printf("NATIVE_IMAGEIO_GLOBAL_PROPERTIES %s\n",[[(id)global description]UTF8String]);
   if(!strcmp(argv[1],"global")){CHECK([[(NSDictionary*)global objectForKey:@"FileSize"]unsignedLongLongValue]==[data length]);CFRelease(global);CFRelease(source);cases++;continue;}
   CFDictionaryRef image=atIndex(source,0,NULL);CHECK(image&&CFGetTypeID(image)==CFDictionaryGetTypeID());CHECK([[(NSDictionary*)image objectForKey:@"PixelWidth"]unsignedLongLongValue]==[fixture[@"width"]unsignedLongLongValue]);CHECK([[(NSDictionary*)image objectForKey:@"PixelHeight"]unsignedLongLongValue]==[fixture[@"height"]unsignedLongLongValue]);
   CHECK(atIndex(source,1,NULL)==NULL);CFRelease(image);CFRelease(global);CFRelease(source);cases++;
  }
 }
 printf("NATIVE_IMAGEIO_REAL_PNG_GIF_TIFF_DATA_URL_PROPERTIES_OK mode=%s cases=%u\n",argv[1],cases);return 0;
}}
