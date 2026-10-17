#include <mach/mach.h>
#include <os/lock.h>
#include <pthread.h>
#include <stdio.h>
#include <unistd.h>

static os_unfair_lock lock = OS_UNFAIR_LOCK_INIT;
static void* worker(void* unused) {
    printf("worker: mach=%u pthread=%u\n", mach_thread_self(), pthread_mach_thread_np(pthread_self()));
    os_unfair_lock_lock(&lock);
    puts("worker acquired lock");
    os_unfair_lock_unlock(&lock);
    return NULL;
}
int main(void) {
    setbuf(stdout, NULL);
    printf("main: mach=%u pthread=%u\n", mach_thread_self(), pthread_mach_thread_np(pthread_self()));
    os_unfair_lock_lock(&lock);
    pthread_t thread;
    if (pthread_create(&thread, NULL, worker, NULL)) return 1;
    usleep(100000);
    os_unfair_lock_unlock(&lock);
    pthread_join(thread, NULL);
    puts("UNFAIR_LOCK_OK");
    return 0;
}
