#include <sys/types.h>
#include <sys/attr.h>
#include <sys/stat.h>
#include <sys/mount.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
static unsigned checks;
#define CHECK(c) do { checks++; if(!(c)) {fprintf(stderr,"METADATA_FAIL line=%d errno=%d: %s\n",__LINE__,errno,#c);exit(1);} }while(0)
static uint32_t u32(const void *p){uint32_t n;memcpy(&n,p,4);return n;}
static uint64_t u64(const void *p){uint64_t n;memcpy(&n,p,8);return n;}
static int query(int kind,int fd,const char *path,struct attrlist *a,void *b,size_t n,unsigned o){
 if(kind==0)return getattrlist(path,a,b,n,o);
 if(kind==1)return getattrlistat(AT_FDCWD,path,a,b,n,o);
 return fgetattrlist(fd,a,b,n,o);
}
static struct attrlist attrs(uint32_t c,uint32_t d,uint32_t f,uint32_t x){struct attrlist a={.bitmapcount=5,.commonattr=c,.dirattr=d,.fileattr=f,.forkattr=x};return a;}
static void bulk_checks(void){
 int fd=open("bulk",O_RDONLY|O_DIRECTORY);CHECK(fd>=0);
 struct attrlist a=attrs(ATTR_BULK_REQUIRED|ATTR_CMN_OBJTYPE|ATTR_CMN_FILEID|ATTR_CMN_ERROR,ATTR_DIR_ENTRYCOUNT,ATTR_FILE_DATALENGTH,0);
 unsigned char buffer[4096];memset(buffer,0xaa,sizeof(buffer));errno=0;
 CHECK(getattrlistbulk(fd,&a,buffer,1,0)==-1&&errno==ERANGE);CHECK(buffer[0]==0xaa);
 unsigned total=0;char seen[40][256];int rc;unsigned calls=0;
 do {
  size_t capacity=(calls++%2)?4096:128;memset(buffer,0xa5,sizeof(buffer));
  rc=getattrlistbulk(fd,&a,buffer,capacity,0);CHECK(rc>=0);size_t at=0;
  for(int i=0;i<rc;i++){
   unsigned char *r=buffer+at;uint32_t n=u32(r);CHECK(n>=48&&n<=capacity-at);
   CHECK(u32(r+4)==(ATTR_BULK_REQUIRED|ATTR_CMN_OBJTYPE|ATTR_CMN_FILEID));CHECK(u32(r+8)==0&&u32(r+20)==0);
   uint32_t name_length=u32(r+28);int32_t offset=(int32_t)u32(r+24);CHECK(offset>=8&&24+offset+name_length<=n&&name_length>1&&name_length<256);
   const char *name=(char*)r+24+offset;CHECK(name[name_length-1]==0);CHECK(strcmp(name,".")&&strcmp(name,".."));CHECK(total<40);
   for(unsigned j=0;j<total;j++)CHECK(strcmp(seen[j],name)!=0);strcpy(seen[total++],name);
   struct stat st;CHECK(fstatat(fd,name,&st,AT_SYMLINK_NOFOLLOW)==0);CHECK(u64(r+36)==st.st_ino);
   uint32_t type=u32(r+32);CHECK(type==(S_ISDIR(st.st_mode)?2:S_ISLNK(st.st_mode)?5:1));
   if(type==2)CHECK(u32(r+12)==ATTR_DIR_ENTRYCOUNT&&u32(r+16)==0&&u32(r+44)==0);
   else CHECK(u32(r+12)==0&&u32(r+16)==ATTR_FILE_DATALENGTH&&u64(r+44)==st.st_size);
   at+=n;
  }
  for(size_t i=at;i<sizeof(buffer);i++)CHECK(buffer[i]==0xa5);
 }while(rc);
 CHECK(total==37&&calls>2);CHECK(getattrlistbulk(fd,&a,buffer,sizeof(buffer),0)==0);
 CHECK(lseek(fd,0,SEEK_SET)==0);
 a=attrs(ATTR_BULK_REQUIRED|ATTR_CMN_ERROR|ATTR_CMN_OBJTYPE,0,0,0);total=0;
 do {
  rc=getattrlistbulk(fd,&a,buffer,sizeof(buffer),FSOPT_PACK_INVAL_ATTRS);CHECK(rc>=0);size_t at=0;
  for(int i=0;i<rc;i++){
   unsigned char *r=buffer+at;CHECK(u32(r+4)==a.commonattr&&u32(r+24)==0);int32_t off=(int32_t)u32(r+28);CHECK(off>=12&&r[28+off]!=0);at+=u32(r);total++;
  }
 }while(rc);
 CHECK(total==37);CHECK(close(fd)==0);
 fd=open("empty",O_RDONLY|O_DIRECTORY);CHECK(fd>=0);CHECK(getattrlistbulk(fd,&a,buffer,sizeof(buffer),0)==0);CHECK(close(fd)==0);
 fd=open("single",O_RDONLY|O_DIRECTORY);CHECK(fd>=0);a=attrs(ATTR_BULK_REQUIRED|ATTR_CMN_OBJTYPE|ATTR_CMN_FILEID,0,0,0);
 memset(buffer,0xcc,sizeof(buffer));CHECK(getattrlistbulk(fd,&a,buffer,52,0)==1&&u32(buffer)==52&&buffer[52]==0xcc);
 CHECK(lseek(fd,0,SEEK_SET)==0);CHECK(getattrlistbulk(fd,&a,buffer,56,0)==1&&u32(buffer)==56);for(int i=52;i<56;i++)CHECK(buffer[i]==0);
 CHECK(close(fd)==0);fd=open("item.bin",O_RDONLY);CHECK(fd>=0);errno=0;CHECK(getattrlistbulk(fd,&a,buffer,sizeof(buffer),0)==-1&&errno==ENOTDIR);CHECK(close(fd)==0);
}
int main(int argc,char **argv){
 CHECK(argc==2);CHECK(chdir(argv[1])==0);
 int fd=open("item.bin",O_RDONLY),directory=open("children",O_RDONLY|O_DIRECTORY);CHECK(fd>=0&&directory>=0);
 struct stat st;struct statfs fs;CHECK(fstat(fd,&st)==0);CHECK(fstatfs(fd,&fs)==0);
 CHECK((uint32_t)fs.f_fsid.val[0]==(uint32_t)st.st_dev);
 unsigned char buffer[4096],second[4096];
 uint32_t common=ATTR_CMN_RETURNED_ATTRS|ATTR_CMN_NAME|ATTR_CMN_DEVID|ATTR_CMN_FSID|ATTR_CMN_OBJTYPE|ATTR_CMN_OWNERID|ATTR_CMN_GRPID|ATTR_CMN_ACCESSMASK|ATTR_CMN_FILEID;
 struct attrlist a=attrs(common,0,ATTR_FILE_DATALENGTH|ATTR_FILE_DATAALLOCSIZE,0);
 for(int k=0;k<3;k++){
  printf("METADATA_ENTRY_KIND %d\n",k);fflush(stdout);memset(buffer,0xcc,sizeof(buffer));CHECK(query(k,fd,"item.bin",&a,buffer,sizeof(buffer),0)==0);
  CHECK(u32(buffer+4)==common);CHECK(u32(buffer+8)==0&&u32(buffer+12)==0&&u32(buffer+16)==a.fileattr&&u32(buffer+20)==0);
  CHECK(u32(buffer+32)==(uint32_t)st.st_dev);CHECK(u64(buffer+36)==u64(&fs.f_fsid));CHECK(u32(buffer+44)==1);
  CHECK(u32(buffer+48)==st.st_uid&&u32(buffer+52)==st.st_gid&&u32(buffer+56)==st.st_mode);CHECK(u64(buffer+60)==st.st_ino);
  CHECK(u64(buffer+68)==st.st_size&&u64(buffer+76)==st.st_blocks*512);
  CHECK(u32(buffer+28)==9&&!strcmp((char*)buffer+24+(int32_t)u32(buffer+24),"item.bin"));CHECK(u32(buffer)==96);
 }
 int parent=open(".",O_RDONLY|O_DIRECTORY);CHECK(parent>=0);
 CHECK(getattrlistat(parent,"item.bin",&a,second,sizeof(second),0)==0&&memcmp(buffer,second,u32(buffer))==0);CHECK(close(parent)==0);
 a=attrs(0,0,0,0);a.volattr=ATTR_VOL_INFO|ATTR_VOL_CAPABILITIES;
 CHECK(fgetattrlist(fd,&a,buffer,sizeof(buffer),0)==0&&u32(buffer)==36);
 vol_capabilities_attr_t caps;memcpy(&caps,buffer+4,sizeof(caps));CHECK(caps.capabilities[VOL_CAPABILITIES_FORMAT]==0&&caps.valid[VOL_CAPABILITIES_FORMAT]==0);
 CHECK(caps.capabilities[VOL_CAPABILITIES_INTERFACES]==VOL_CAP_INT_ATTRLIST&&caps.valid[VOL_CAPABILITIES_INTERFACES]==(VOL_CAP_INT_ATTRLIST|VOL_CAP_INT_READDIRATTR));
 a.commonattr=ATTR_CMN_RETURNED_ATTRS;a.volattr|=ATTR_VOL_ATTRIBUTES;
 CHECK(fgetattrlist(fd,&a,buffer,sizeof(buffer),0)==0&&u32(buffer)==96&&u32(buffer+8)==a.volattr);
 vol_attributes_attr_t supported;memcpy(&supported,buffer+56,sizeof(supported));CHECK(supported.validattr.commonattr&ATTR_CMN_FILEID);CHECK(!(supported.validattr.commonattr&(ATTR_CMN_GEN_COUNT|ATTR_CMN_ADDEDTIME|ATTR_CMN_DATA_PROTECT_FLAGS)));
 for(unsigned i=0;i<5;i++)CHECK((((uint32_t*)&supported.nativeattr)[i]&~((uint32_t*)&supported.validattr)[i])==0);
 a.volattr=ATTR_VOL_INFO|ATTR_VOL_UUID;errno=0;CHECK(fgetattrlist(fd,&a,buffer,sizeof(buffer),0)==-1&&errno==ENOTSUP);
 a=attrs(ATTR_CMN_RETURNED_ATTRS|ATTR_CMN_FNDRINFO,0,ATTR_FILE_RSRCLENGTH|ATTR_FILE_TOTALSIZE,0);
 CHECK(fgetattrlist(fd,&a,buffer,sizeof(buffer),0)==0);CHECK(u32(buffer+4)==a.commonattr&&u32(buffer+16)==a.fileattr);
 for(unsigned i=0;i<32;i++)CHECK(buffer[24+i]==(unsigned char)(i*7+3));
 CHECK(u64(buffer+56)==1234+259&&u64(buffer+64)==259);CHECK(u32(buffer)==72);
 a=attrs(ATTR_CMN_RETURNED_ATTRS|ATTR_CMN_FILEID|ATTR_CMN_GEN_COUNT|ATTR_CMN_ADDEDTIME,0,0,ATTR_CMNEXT_REALDEVID|ATTR_CMNEXT_EXT_FLAGS);
 CHECK(fgetattrlist(fd,&a,buffer,sizeof(buffer),FSOPT_ATTR_CMN_EXTENDED)==0);
 CHECK(u32(buffer)==36&&u32(buffer+4)==(ATTR_CMN_RETURNED_ATTRS|ATTR_CMN_FILEID)&&u32(buffer+20)==ATTR_CMNEXT_REALDEVID);
 CHECK(u64(buffer+24)==st.st_ino&&u32(buffer+32)==(uint32_t)st.st_dev);
 memset(buffer,0xcc,sizeof(buffer));CHECK(fgetattrlist(fd,&a,buffer,sizeof(buffer),FSOPT_ATTR_CMN_EXTENDED|FSOPT_PACK_INVAL_ATTRS)==0);
 CHECK(u32(buffer)==64&&u32(buffer+4)==(ATTR_CMN_RETURNED_ATTRS|ATTR_CMN_FILEID)&&u32(buffer+20)==ATTR_CMNEXT_REALDEVID);
 CHECK(u32(buffer+24)==0&&u64(buffer+28)==st.st_ino);for(int i=36;i<52;i++)CHECK(buffer[i]==0);
 CHECK(u32(buffer+52)==(uint32_t)st.st_dev&&u64(buffer+56)==0);
 a=attrs(ATTR_CMN_RETURNED_ATTRS|ATTR_CMN_NAME|ATTR_CMN_ERROR|ATTR_CMN_FILEID,0,0,0);
 CHECK(fgetattrlist(fd,&a,buffer,sizeof(buffer),FSOPT_PACK_INVAL_ATTRS)==0);CHECK(u32(buffer+24)==0);CHECK(u64(buffer+36)==st.st_ino);
 a=attrs(ATTR_CMN_RETURNED_ATTRS|ATTR_CMN_NAME|ATTR_CMN_FILEID,0,ATTR_FILE_DATALENGTH,0);
 CHECK(fgetattrlist(fd,&a,buffer,sizeof(buffer),FSOPT_REPORT_FULLSIZE)==0);unsigned needed=u32(buffer);CHECK(needed>40&&needed<4096);
 size_t page=getpagesize();unsigned char *guard=mmap(NULL,page*3,PROT_NONE,MAP_PRIVATE|MAP_ANON,-1,0);CHECK(guard!=MAP_FAILED);CHECK(mprotect(guard+page,page,PROT_READ|PROT_WRITE)==0);
 for(unsigned n=1;n<=needed+8;n++)for(int full=0;full<2;full++){
  unsigned char *dst=guard+page*2-n;memset(dst,0xac,n);CHECK(fgetattrlist(fd,&a,dst,n,full?FSOPT_REPORT_FULLSIZE:0)==0);
  memcpy(second,buffer,needed);uint32_t length=full?needed:(n<needed?n:needed);memcpy(second,&length,4);
  CHECK(!memcmp(dst,second,n<needed?n:needed));for(unsigned j=needed;j<n;j++)CHECK(dst[j]==0xac);
 }
 CHECK(munmap(guard,page*3)==0);
 a=attrs(ATTR_CMN_RETURNED_ATTRS|ATTR_CMN_OBJTYPE,0,0,0);
 CHECK(getattrlist("link",&a,buffer,sizeof(buffer),0)==0&&u32(buffer+24)==1);
 CHECK(getattrlist("link",&a,buffer,sizeof(buffer),FSOPT_NOFOLLOW)==0&&u32(buffer+24)==5);
 a=attrs(ATTR_CMN_RETURNED_ATTRS,ATTR_DIR_ENTRYCOUNT,0,0);
 DIR *dir=fdopendir(directory);CHECK(dir!=NULL);CHECK(readdir(dir)!=NULL);off_t cursor=lseek(directory,0,SEEK_CUR);CHECK(cursor>=0);
 CHECK(fgetattrlist(directory,&a,buffer,sizeof(buffer),0)==0&&u32(buffer+24)==2);CHECK(lseek(directory,0,SEEK_CUR)==cursor);
 CHECK(closedir(dir)==0);
 a=attrs(ATTR_CMN_RETURNED_ATTRS,0,ATTR_FILE_DATALENGTH|ATTR_FILE_DATAALLOCSIZE,0);
 CHECK(getattrlist("sparse.bin",&a,buffer,sizeof(buffer),0)==0);CHECK(u64(buffer+24)==104857600&&u64(buffer+32)<u64(buffer+24));
 a=attrs(ATTR_CMN_RETURNED_ATTRS|ATTR_CMN_OBJTYPE,0,0,0);
 errno=0;CHECK(getattrlist("missing",&a,buffer,sizeof(buffer),0)==-1&&errno==ENOENT);
 errno=0;CHECK(fgetattrlist(-1,&a,buffer,sizeof(buffer),0)==-1&&errno==EBADF);
 a.bitmapcount=4;errno=0;CHECK(fgetattrlist(fd,&a,buffer,sizeof(buffer),0)==-1&&errno==EINVAL);a.bitmapcount=5;
 errno=0;CHECK(fgetattrlist(fd,&a,buffer,0,0)==-1&&errno==EINVAL);
 a=attrs(ATTR_CMN_GEN_COUNT,0,0,0);errno=0;CHECK(fgetattrlist(fd,&a,buffer,sizeof(buffer),FSOPT_ATTR_CMN_EXTENDED)==-1&&errno==EINVAL);
 a=attrs(ATTR_CMN_NAME,0,0,0);errno=0;CHECK(fgetattrlist(fd,&a,buffer,sizeof(buffer),FSOPT_PACK_INVAL_ATTRS)==-1&&errno==EINVAL);
 CHECK(close(fd)==0);bulk_checks();
 int count=getfsstat(NULL,0,MNT_NOWAIT);CHECK(count>0&&count<4096);struct statfs *mounts=calloc(count+32,sizeof(*mounts));CHECK(mounts!=NULL);
 int got=getfsstat(mounts,(count+32)*sizeof(*mounts),MNT_NOWAIT);CHECK(got==count);
 for(int i=0;i<got;i++){CHECK(mounts[i].f_mntonname[0]=='/');for(int j=0;j<i;j++)CHECK(memcmp(&mounts[i].f_fsid,&mounts[j].f_fsid,sizeof(fsid_t))!=0);}
 CHECK(getfsstat(mounts,sizeof(*mounts),MNT_NOWAIT)==1);free(mounts);
 printf("METADATA_KERNEL_PASS checks=%u unique_filesystems=%d\n",checks,got);return 0;
}
