#include <sys/quota.h>
#include <sys/errno.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
int main(int argc,char **argv) {
    if(argc!=3)return 2;
    int expected=atoi(argv[2]);unsigned checks=0;
    for(unsigned type=0;type<2;type++){
        struct dqblk value;memset(&value,0x5a,sizeof(value));struct dqblk previous=value;
        errno=0;int result=quotactl(argv[1],QCMD(Q_GETQUOTA,type),0,(void*)&value);
        printf("QUOTA_ACTUAL_QUERY type=%u result=%d errno=%d\n",type,result,errno);
        if(result!=-1||errno!=expected||memcmp(&value,&previous,sizeof(value)))return 3;checks++;
        int enabled=0x12345678;errno=0;result=quotactl(argv[1],QCMD(Q_QUOTASTAT,type),0,(void*)&enabled);
        if(result!=-1||errno!=expected||enabled!=0x12345678)return 4;checks++;
    }
    errno=0;if(quotactl("/this-path-must-not-exist-quota",QCMD(Q_GETQUOTA,0),0,NULL)!=-1||errno!=ENOENT)return 5;checks++;
    errno=0;if(quotactl((void*)1,QCMD(Q_GETQUOTA,0),0,NULL)!=-1||errno!=EFAULT)return 6;checks++;
    errno=0;if(quotactl(argv[1],QCMD(Q_GETQUOTA,2),0,NULL)!=-1||errno!=EINVAL)return 7;checks++;
    errno=0;if(quotactl(argv[1],QCMD(Q_SETQUOTA,0),0,NULL)!=-1||errno!=ENOTSUP)return 8;checks++;
    printf("QUOTACTL_SOURCE_REAL_LINUX_BACKEND_UNSUPPORTED_FILESYSTEM_AND_ERRORS_OK checks=%u\n",checks);
    return 0;
}
