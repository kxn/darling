#include <CoreServices/CoreServices.h>
#include <CoreFoundation/CoreFoundation.h>
#include <sys/mount.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef int (*MountPoints)(CFAllocatorRef,Boolean,char (**)[1024],CFIndex *);
static void volumes(const char *label) {
 MountPoints fn=(MountPoints)dlsym(RTLD_DEFAULT,"FileIDTreeCreateMountPointArrayWithOptions");
 char (*paths)[1024]=NULL;CFIndex count=0;int status=fn?fn(NULL,false,&paths,&count):-1;
 printf("LEGACY_MOUNT_POINTS stage=%s status=%d count=%ld\n",label,status,(long)count);
 for(CFIndex i=0;i<count;i++)printf("LEGACY_MOUNT path=%s\n",paths[i]);
 if(paths)CFAllocatorDeallocate(NULL,paths);
 CFURLEnumeratorRef en=CFURLEnumeratorCreateForMountedVolumes(NULL,0,NULL);
 unsigned n=0;CFIndex result=0;CFErrorRef error=NULL;
 if(en){CFURLRef url;while((result=CFURLEnumeratorGetNextURL(en,&url,&error))==1&&n<100)n++;CFRelease(en);}
 printf("LEGACY_CF_VOLUMES stage=%s count=%u result=%ld error=%ld\n",label,n,(long)result,error?(long)CFErrorGetCode(error):0);
}
int main(void) {
 setbuf(stdout,NULL);volumes("before");
 struct statfs *mounts=NULL;int count=getmntinfo(&mounts,MNT_NOWAIT);
 for(int i=0;i<count;i++) {
  char path[1024];strlcpy(path,mounts[i].f_mntonname,sizeof(path));
  FSRef ref;Boolean dir=0;OSStatus result=FSPathMakeRef((UInt8*)path,&ref,&dir);
  printf("LEGACY_PATH_REF path=%s result=%d directory=%u\n",path,(int)result,dir);
  if(!result){FSCatalogInfo info;memset(&info,0,sizeof(info));result=FSGetCatalogInfo(&ref,kFSCatInfoVolume|kFSCatInfoNodeID,&info,NULL,NULL,NULL);printf("LEGACY_CATALOG path=%s result=%d volume=%d inode=%u\n",path,(int)result,info.volume,info.nodeID);}
 }
 volumes("after_paths");
 for(unsigned i=1;i<32;i++) {
  FSVolumeRefNum volume=0;OSErr status=FSGetVolumeInfo(0,i,&volume,kFSVolInfoNone,NULL,NULL,NULL);
  printf("LEGACY_VOLUME_INDEX index=%u status=%d volume=%d\n",i,status,volume);
  if(status)break;
 }
 volumes("after_index");puts("NATIVE_LEGACY_VOLUME_REFERENCE_PROBE_RETURNED");return 0;
}
