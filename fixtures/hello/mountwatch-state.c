#include "mountwatch_state.h"
#include <stdio.h>
static unsigned checks;
#define check(c) do{++checks;if(!(c)){fprintf(stderr,"MOUNTWATCH_STATE_FAIL line=%d check=%u\n",__LINE__,checks);exit(1);}}while(0)
static const char* root="1 0 0:1 / / rw shared:7 - overlay overlay rw\n";
static const char* mount="2 1 0:9 / /Volumes/test rw,nosuid - tmpfs tmpfs rw,size=1024k\n";
static unsigned delta(const char* a,const char* b){struct dw_mount_snapshot x={0},y={0};check(dw_mount_parse(a,strlen(a),&x));check(dw_mount_parse(b,strlen(b),&y));unsigned d=dw_mount_changes(&x,&y);dw_mount_free(&x);dw_mount_free(&y);return d;}
int main(void){
 char both[1024],reverse[1024],remount[1024],reused[1024];snprintf(both,sizeof(both),"%s%s",root,mount);snprintf(reverse,sizeof(reverse),"%s%s",mount,root);
 snprintf(remount,sizeof(remount),"%s2 1 0:9 / /Volumes/test ro,nosuid - tmpfs tmpfs ro,size=1024k\n",root);
 snprintf(reused,sizeof(reused),"%s2 1 0:10 / /Volumes/test rw,nosuid - tmpfs tmpfs rw,size=1024k\n",root);
 check(delta(root,root)==0);check(delta(root,both)==DW_MOUNT_ADD);check(delta(both,root)==DW_MOUNT_REMOVE);
 check(delta(both,reverse)==0);check(delta(both,remount)==DW_MOUNT_UPDATE);check(delta(both,reused)==(DW_MOUNT_REMOVE|DW_MOUNT_ADD));
 const char* bad[]={"","1 0 0:1 / / rw - overlay overlay rw","0 0 0:1 / / rw - overlay overlay rw\n","18446744073709551616 0 0:1 / / rw - overlay overlay rw\n","1 0 0:1 / / rw - overlay\n","1 0 0:1 relative / rw - overlay overlay rw\n","1 0 invalid / / rw - overlay overlay rw\n",NULL};
 for(unsigned i=0;bad[i];i++){struct dw_mount_snapshot s={0};check(!dw_mount_parse(bad[i],strlen(bad[i]),&s));dw_mount_free(&s);}
 char duplicate[1024];snprintf(duplicate,sizeof(duplicate),"%s%s",root,root);struct dw_mount_snapshot s={0};check(!dw_mount_parse(duplicate,strlen(duplicate),&s));
 for(size_t length=0;length<strlen(both);length++){int good=dw_mount_parse(both,length,&s);if(length!=strlen(root))check(!good);dw_mount_free(&s);}
 FILE* file=fopen("/proc/self/mountinfo","r");check(file);char buffer[1024*1024];size_t length=fread(buffer,1,sizeof(buffer),file);check(!ferror(file)&&feof(file));fclose(file);
 check(dw_mount_parse(buffer,length,&s));check(s.count>0);check(dw_mount_changes(&s,&s)==0);size_t real=s.count;dw_mount_free(&s);
 printf("LINUX_MOUNTWATCH_STATE_OK checks=%u real_namespace_records=%zu\n",checks,real);return 0;
}
