/* Opt-in diagnostic only: let the host debugger attach before original main. */
#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
__attribute__((constructor)) static void wait_for_debugger(void){
 fprintf(stderr,"DARLING_LAUNCH_DEBUG_READY %d\n",getpid());fflush(stderr);
 FILE *gate=fopen("/Volumes/SystemRoot/workspace/runtime/coretypes-debug-release","r");
 if(!gate){perror("Darling debug gate");_exit(2);}fgetc(gate);fclose(gate);
}
