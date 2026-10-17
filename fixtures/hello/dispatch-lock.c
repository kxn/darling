#include <dispatch/dispatch.h>
#include <mach/mach.h>
#include <os/lock.h>
#include <pthread.h>
#include <stdio.h>
#include <unistd.h>

extern void os_unfair_lock_lock_with_options(os_unfair_lock_t, unsigned int);
static os_unfair_lock lock = OS_UNFAIR_LOCK_INIT;
static unsigned int counter;
int main(void) {
    setbuf(stdout, NULL);
    dispatch_apply(32, dispatch_get_global_queue(QOS_CLASS_DEFAULT, 0), ^(size_t index) {
        os_unfair_lock_lock_with_options(&lock, 0x50000);
        ++counter;
        usleep(1000);
        os_unfair_lock_unlock(&lock);
    });
    printf("counter=%u\n", counter);
    return counter == 32 ? 0 : 1;
}
