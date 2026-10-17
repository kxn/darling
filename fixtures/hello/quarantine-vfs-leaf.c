#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
int main(int argc,char **argv){
    if(argc==2){int fd=open(argv[1],O_WRONLY|O_CREAT|O_EXCL,0600);if(fd<0)return 3;if(write(fd,"leaf",4)!=4)return 4;close(fd);}
    puts("QUARANTINE_EXEC_LEAF_ACTUALLY_RAN");return 0;
}
