#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <poll.h>

extern int _pthread_workqueue_init(void (*)(unsigned long), int, int);
extern int _pthread_workqueue_addthreads(int, unsigned long);
static int channel[2];
static pthread_key_t key;
struct sample { uintptr_t thread, address, top; unsigned long priority; int exited; };
static void send_sample(struct sample *s) {
    if (write(channel[1], s, sizeof(*s)) != sizeof(*s)) _exit(91);
}
static void destroyed(void *p) {
    struct sample s = { .thread=(uintptr_t)pthread_self(), .exited=1 };
    send_sample(&s);
}
static void work(unsigned long priority) {
    volatile char marker;
    struct sample s = { (uintptr_t)pthread_self(), (uintptr_t)&marker,
        (uintptr_t)pthread_get_stackaddr_np(pthread_self()), priority, 0 };
    if (pthread_setspecific(key, (void *)1)) _exit(92);
    send_sample(&s);
}
static struct sample receive(void) {
    struct pollfd fd={channel[0], POLLIN, 0};
    struct sample s;
    if (poll(&fd, 1, 20000)!=1 || read(channel[0], &s, sizeof(s))!=sizeof(s)) {
        fprintf(stderr,"WORKQUEUE_REPLY_OR_IDLE_EXIT_TIMEOUT\n"); exit(93);
    }
    return s;
}
int main(void) {
    if (pipe(channel) || pthread_key_create(&key, destroyed)) return 94;
    int err=_pthread_workqueue_init(work, 0, 0);
    if(err) { fprintf(stderr,"workqueue init=%d\n",err); return 95; }
    uintptr_t owner=0, lowest=UINTPTR_MAX, highest=0;
    /* No queued user blocks: every returned callback parks in the kernel
       emulation before the next request, exercising the actual reuse entry. */
    for(int i=0;i<2048;i++) {
        if(_pthread_workqueue_addthreads(1, 0x8ff)) return 96;
        struct sample s=receive();
        if(s.exited || !s.thread || s.top<=s.address || s.top-s.address>512*1024) return 97;
        if(!owner) owner=s.thread;
        if(s.thread!=owner) { fprintf(stderr,"unexpected worker replacement\n");return 98; }
        if(s.address<lowest) lowest=s.address;
        if(s.address>highest) highest=s.address;
        if(highest-lowest>16384) {
            fprintf(stderr,"WORKQUEUE_REUSE_STACK_GROWTH rounds=%d bytes=%lu\n",i+1,(unsigned long)(highest-lowest));
            return 42;
        }
        usleep(1000);
    }
    printf("WORKQUEUE_REAL_2048_SAME_THREAD_REUSES_STACK_SPAN=%lu\n",(unsigned long)(highest-lowest));
    fflush(stdout);
    /* The idle timeout re-enters the same trampoline with nkevents=-1;
       observe actual pthread cleanup instead of killing the worker. */
    struct sample ended=receive();
    if(!ended.exited || ended.thread!=owner) return 99;
    puts("WORKQUEUE_REAL_IDLE_TIMEOUT_PTHREAD_DESTRUCTOR_OK");
    return 0;
}
