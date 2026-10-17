#import <Foundation/Foundation.h>
#import <CoreFoundation/CoreFoundation.h>
#include <sys/mount.h>
#include <stdbool.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
extern Boolean SecTranslocateIsTranslocatedURL(CFURLRef,bool *,CFErrorRef *);
extern CFURLRef SecTranslocateCreateOriginalPathForURL(CFURLRef,CFErrorRef *);
int main(int argc,char **argv){setbuf(stdout,NULL);@autoreleasepool {
 if(argc>1&&!strcmp(argv[1],"--wait")){printf("TRANSLOCATION_READY %d\n",getpid());FILE *f=fopen("/Volumes/SystemRoot/workspace/runtime/coretypes-debug-release","r");if(!f)return 2;fgetc(f);fclose(f);}
 const char *path="/System/Library/CoreServices/CoreTypes.bundle";struct statfs fs;int rc=statfs(path,&fs);printf("TRANSLOCATION_STATFS %d errno=%d type=%s\n",rc,errno,rc?"?":fs.f_fstypename);
 NSURL *url=[NSURL fileURLWithPath:@"/System/Library/CoreServices/CoreTypes.bundle" isDirectory:YES];
 char bytes[4096];Boolean converted=CFURLGetFileSystemRepresentation((CFURLRef)url,true,(UInt8*)bytes,sizeof(bytes));printf("TRANSLOCATION_URL_PATH ok=%d path=%s\n",converted,converted?bytes:"?");
 bool translocated=true;CFErrorRef error=NULL;Boolean ok=SecTranslocateIsTranslocatedURL((CFURLRef)url,&translocated,&error);
 printf("TRANSLOCATION_IS ok=%d value=%d error=%s\n",ok,translocated,[[(NSError*)error description] UTF8String]);if(error)CFRelease(error);
 CFBundleRef bundle=CFBundleCreate(NULL,(CFURLRef)url);printf("TRANSLOCATION_CFBUNDLE created=%d\n",bundle!=NULL);if(bundle)CFRelease(bundle);
 error=NULL;CFURLRef original=SecTranslocateCreateOriginalPathForURL((CFURLRef)url,&error);printf("TRANSLOCATION_ORIGINAL created=%d error=%s\n",original!=NULL,[[(NSError*)error description] UTF8String]);if(original)CFRelease(original);if(error)CFRelease(error);
 return !(rc==0&&converted&&ok&&!translocated&&bundle&&original);
}}
