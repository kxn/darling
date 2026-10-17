#include <assert.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>

/* Pinned MetadataUtilities export: zero-filled 40-byte thread template. */
extern _Thread_local unsigned char si_tracing_current_span[40];
static pthread_mutex_t mutex=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t condition=PTHREAD_COND_INITIALIZER;
static unsigned ready;
static int release_threads;
static unsigned char *addresses[2];
static void *work(void *argument) {
    unsigned index=(unsigned)(unsigned long)argument;
    for (unsigned i=0;i<40;i++)assert(si_tracing_current_span[i]==0);
    memset(si_tracing_current_span,0x31+index,40);
    pthread_mutex_lock(&mutex);
    addresses[index]=si_tracing_current_span;ready++;
    pthread_cond_broadcast(&condition);
    while (!release_threads)pthread_cond_wait(&condition,&mutex);
    pthread_mutex_unlock(&mutex);
    for (unsigned i=0;i<40;i++)assert(si_tracing_current_span[i]==0x31+index);
    return NULL;
}
int main(void) {
    for (unsigned i=0;i<40;i++)assert(si_tracing_current_span[i]==0);
    memset(si_tracing_current_span,0x73,40);
    pthread_t threads[2];
    for (unsigned long i=0;i<2;i++)assert(!pthread_create(&threads[i],NULL,work,(void *)i));
    pthread_mutex_lock(&mutex);
    while (ready!=2)pthread_cond_wait(&condition,&mutex);
    assert(addresses[0]!=addresses[1] && addresses[0]!=si_tracing_current_span && addresses[1]!=si_tracing_current_span);
    for (unsigned i=0;i<40;i++)assert(si_tracing_current_span[i]==0x73);
    release_threads=1;pthread_cond_broadcast(&condition);pthread_mutex_unlock(&mutex);
    for (unsigned i=0;i<2;i++)assert(!pthread_join(threads[i],NULL));
    puts("ORIGINAL_METADATA_EXPORTED_TLV_THREE_THREADS_ZERO_INITIALIZATION_DISTINCT_STORAGE_ISOLATION_OK");
    return 0;
}
