#import <Foundation/Foundation.h>
#include <sys/mount.h>
#include <stdio.h>
#include <errno.h>
#include <dlfcn.h>
#include <objc/runtime.h>
int main(void) {
 setbuf(stdout,NULL);
 @autoreleasepool {
  Method method=class_getInstanceMethod([NSFileManager class],@selector(mountedVolumeURLsIncludingResourceValuesForKeys:options:));Dl_info owner={0};void *implementation=(void *)method_getImplementation(method);dladdr(implementation,&owner);
  printf("VOLUME_METHOD_OWNER %p %s %s\n",implementation,owner.dli_fname,owner.dli_sname?owner.dli_sname:"");
  void *enumerate=dlsym(RTLD_DEFAULT,"CFURLEnumeratorCreateForMountedVolumes");memset(&owner,0,sizeof(owner));if(enumerate)dladdr(enumerate,&owner);printf("VOLUME_ENUMERATOR_OWNER %p %s %s\n",enumerate,owner.dli_fname?owner.dli_fname:"nil",owner.dli_sname?owner.dli_sname:"");
  struct statfs *entries=NULL;errno=0;int count=getmntinfo(&entries,MNT_NOWAIT);
  printf("NATIVE_VOLUMES_GETMNTINFO count=%d errno=%d size=%zu\n",count,errno,sizeof(struct statfs));
  for(int i=0;i<count&&i<100;i++)printf("MOUNT %s %s %s flags=%llx fsid=%x:%x\n",entries[i].f_mntonname,entries[i].f_mntfromname,entries[i].f_fstypename,(unsigned long long)entries[i].f_flags,entries[i].f_fsid.val[0],entries[i].f_fsid.val[1]);
  struct statfs *owned=NULL;errno=0;int reentrant=getmntinfo_r_np(&owned,MNT_NOWAIT);printf("NATIVE_VOLUMES_GETMNTINFO_R count=%d errno=%d buffer=%p\n",reentrant,errno,owned);free(owned);
  typedef int (*MountPoints)(CFAllocatorRef,Boolean,char (**)[1024],CFIndex *);
  MountPoints mountPoints=(MountPoints)dlsym(RTLD_DEFAULT,"FileIDTreeCreateMountPointArrayWithOptions");
  if(mountPoints){char (*paths)[1024]=NULL;CFIndex n=0;memset(&owner,0,sizeof(owner));dladdr((void *)mountPoints,&owner);int status=mountPoints(NULL,false,&paths,&n);printf("FILEIDTREE_MOUNT_POINTS status=%d count=%ld owner=%s\n",status,(long)n,owner.dli_fname);if(paths)CFAllocatorDeallocate(NULL,paths);}
  CFURLEnumeratorRef enumerator=CFURLEnumeratorCreateForMountedVolumes(NULL,0,NULL);printf("CF_MOUNT_ENUMERATOR %p\n",enumerator);
  if(enumerator) {
   for(unsigned i=0;i<100;i++) {CFURLRef url=NULL;CFErrorRef error=NULL;CFIndex result=CFURLEnumeratorGetNextURL(enumerator,&url,&error);char domain[128]={0};if(error)CFStringGetCString(CFErrorGetDomain(error),domain,sizeof(domain),kCFStringEncodingUTF8);printf("CF_MOUNT_ENUMERATOR_NEXT result=%ld url=%p error_domain=%s error_code=%ld\n",(long)result,url,domain,error?(long)CFErrorGetCode(error):0);if(result!=1)break;}
   CFRelease(enumerator);
  }
  NSArray *urls=[[NSFileManager defaultManager] mountedVolumeURLsIncludingResourceValuesForKeys:nil options:0];
  printf("NATIVE_VOLUMES_FOUNDATION count=%lu nil=%d\n",(unsigned long)[urls count],urls==nil);
  for(NSURL *url in urls) {
   printf("VOLUME %s\n",[[url path] UTF8String]);
   for(NSString *key in @[NSURLVolumeUUIDStringKey,NSURLVolumeNameKey,NSURLVolumeURLKey,NSURLVolumeIsLocalKey,NSURLVolumeSupportsFileProtectionKey]) {
    id value=nil;NSError *error=nil;BOOL ok=[url getResourceValue:&value forKey:key error:&error];
    printf("VOLUME_PROPERTY %s ok=%d value=%s error=%s\n",[key UTF8String],ok,[[value description] UTF8String],[[error description] UTF8String]);
   }
  }
  puts("NATIVE_VOLUMES_PROBE_RETURNED");
 }
 return 0;
}
