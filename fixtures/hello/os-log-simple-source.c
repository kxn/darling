#include <assert.h>
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <mach-o/dyld.h>
#include <mach-o/loader.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <unistd.h>
#include <uuid/uuid.h>
/* Independent declarations of the upstream public payload and on-wire ABI. */
typedef struct {
    uint8_t type; const char *subsystem, *message;
    uint64_t timestamp, pid, unique_pid, pid_version, tid, relative_offset;
    uuid_t sender_uuid, process_uuid, dsc_uuid;
} payload_t;
typedef struct {
    uint16_t message_size, subsystem_size; uint8_t type;
    uint64_t timestamp, pid, unique_pid, pid_version, tid, relative_offset;
    uuid_t sender_uuid, process_uuid, dsc_uuid;
    char data[];
} wire_t;
typedef void (*log_fn)(const struct mach_header *, uuid_t, uuid_t, uintptr_t, uint8_t, const char *, const char *, ...);
typedef void (*offset_fn)(const struct mach_header *, const uuid_t, const uuid_t, uintptr_t, uint64_t, uint8_t, const char *, const char *);
static log_fn emit;
static int (*send_payload)(payload_t *);
static int (*parse)(const char *, size_t, payload_t *);
static uint64_t (*now)(void);
static int receiver;
static unsigned checked;
static pid_t expected_child;
static unsigned char sender_uuid[16], dsc_uuid[16];

static size_t receive_record(char buffer[2048], payload_t *out) {
    ssize_t length = recv(receiver, buffer, 2048, 0); assert(length >= 104);
    assert(parse(buffer, length, out) == 0);
    assert((out->pid == getpid() || (expected_child > 0 && out->pid == expected_child)) && out->timestamp && out->timestamp <= now());
    assert(out->message >= buffer + 104 && out->message < buffer + length);
    wire_t *wire = (wire_t *)buffer;
    assert((size_t)length == sizeof(*wire) + wire->message_size + wire->subsystem_size);
    checked++; return length;
}
static void *worker(void *argument) {
    unsigned n = (unsigned)(uintptr_t)argument;
    for (unsigned j = 0; j < 16; j++)
        emit(NULL, sender_uuid, dsc_uuid, 0, 1, "threads", "thread %u record %u", n, j);
    return NULL;
}
int main(int argc, char **argv) {
    assert(argc >= 3); setbuf(stdout, NULL);
    assert(sizeof(wire_t) == 104 && sizeof(payload_t) == 120);
    char directory[] = "/Volumes/SystemRoot/workspace/artifacts/simple-log-XXXXXX";
    assert(mkdtemp(directory)); char path[104]; snprintf(path, sizeof(path), "%s/socket", directory);
    setenv("DARLING_SIMPLE_LOG_SOCKET", path, 1);
    void *system = dlopen(argv[1], RTLD_LAZY); assert(system);
    emit = (log_fn)dlsym(system, "_os_log_simple");
    offset_fn offset = (offset_fn)dlsym(system, "__os_log_simple_offset");
    void (*shim)(uint8_t,const char*,const char*) = dlsym(system, "_os_log_simple_shim");
    void (*reinit)(void) = dlsym(system, "_os_log_simple_reinit_4launchd");
    send_payload = dlsym(system, "_os_log_simple_send"); parse = dlsym(system, "_os_log_simple_parse");
    now = dlsym(system, "os_log_simple_now"); uint8_t (*level)(int) = dlsym(system,"os_log_simple_type_from_asl");
    assert(emit && offset && shim && send_payload && parse && now && level && reinit);
    Dl_info owner; assert(dladdr((void *)emit, &owner) && !strcmp(owner.dli_fname, argv[2]));
    payload_t seed = {.type=0, .message="retry", .pid=getpid(), .timestamp=now()};
    assert(send_payload(&seed) == EBADF); /* No receiver exists; never report delivery. */
    receiver = socket(AF_UNIX, SOCK_DGRAM, 0); assert(receiver >= 0);
    struct sockaddr_un address = {0}; address.sun_family=AF_UNIX; address.sun_len=sizeof(address);
    strlcpy(address.sun_path,path,sizeof(address.sun_path));
    assert(bind(receiver,(const struct sockaddr *)&address,sizeof(address))==0);
    struct timeval timeout = {.tv_sec=5}; assert(setsockopt(receiver,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout))==0);
    reinit(); assert(send_payload(&seed)==0);
    char buffer[2048]; payload_t out;
    receive_record(buffer,&out); assert(!strcmp(out.message,"retry"));
    puts("SOURCE_SIMPLE_LOG_REAL_ABSENT_SOCKET_ERROR_AND_LAUNCHD_RECONNECT_OK");
    const struct mach_header *header = _dyld_get_image_header(0); assert(header);
    for (unsigned i=0;i<16;i++) {sender_uuid[i]=0xa0+i;dsc_uuid[i]=0xb0+i;}
    uint64_t tid; assert(!pthread_threadid_np(NULL,&tid));
    setenv("DARLING_OS_LOG_STDERR","1",1);
    emit(header,sender_uuid,dsc_uuid,0,16,"linuxcode.simple", "SIMPLE_LOG_E2E %s %d %lld %llx %c %%", "日志",-77,(long long)INT64_MIN,UINT64_MAX,'Z');
    unsetenv("DARLING_OS_LOG_STDERR");
    size_t length=receive_record(buffer,&out);
    assert(!strcmp(out.message,"SIMPLE_LOG_E2E 日志 -77 -9223372036854775808 ffffffffffffffff Z %"));
    assert(!strcmp(out.subsystem,"linuxcode.simple") && out.type==16 && out.tid==tid);
    assert(!memcmp(out.sender_uuid,sender_uuid,16) && !memcmp(out.dsc_uuid,dsc_uuid,16));
    assert(out.relative_offset && out.relative_offset < UINT64_C(0x10000000));
    /* Every short prefix is placed against PROT_NONE, detecting overreads. */
    size_t page=getpagesize(); char *guard=mmap(NULL,2*page,PROT_READ|PROT_WRITE,MAP_ANON|MAP_PRIVATE,-1,0);
    assert(guard!=MAP_FAILED && !mprotect(guard+page,page,PROT_NONE));
    for (size_t n=0;n<length;n++) {char *p=guard+page-n;memcpy(p,buffer,n);assert(parse(p,n,&out)!=0);}
    assert(!munmap(guard,2*page));
    wire_t *wire=(wire_t *)buffer; wire_t saved=*wire;
    wire->type=3;assert(parse(buffer,length,&out)==EINVAL);*wire=saved;
    wire->pid=0;assert(parse(buffer,length,&out)==EINVAL);*wire=saved;
    wire->timestamp=UINT64_MAX;assert(parse(buffer,length,&out)==EINVAL);*wire=saved;
    wire->data[wire->message_size-1]='x';assert(parse(buffer,length,&out)==EINVAL);
    puts("SOURCE_SIMPLE_LOG_REAL_VARARGS_UTF8_IDS_UUID_OFFSET_AND_GUARD_PAGE_PARSER_OK");
    offset(header,sender_uuid,dsc_uuid,0,(uintptr_t)header+0x1234,0,NULL,"offset");
    receive_record(buffer,&out); assert(out.relative_offset==0x1234 && !out.subsystem && !strcmp(out.message,"offset"));
    struct mach_header cached=*header; cached.flags |= MH_DYLIB_IN_CACHE;
    offset(&cached,sender_uuid,dsc_uuid,0x1000,0x2234,2,"cache","cache offset");
    receive_record(buffer,&out); assert(out.relative_offset==0x1234 && out.type==2);
    shim(1,NULL,"fallback sender"); receive_record(buffer,&out);
    assert(!memcmp(out.sender_uuid,out.process_uuid,16));
    for (int i=-1;i<=8;i++) {uint8_t expected=i<4?16:i<6?0:i==6?1:2;assert(level(i)==expected);}
    for (unsigned n=1942;n<=1944;n++) {
        char text[1945]; memset(text,'A',n);text[n]=0;
        seed.message=text;seed.timestamp=now();int error=send_payload(&seed);
        if (n==1944) assert(error==E2BIG);
        else {assert(!error);receive_record(buffer,&out);assert(strlen(out.message)==n);}
    }
    puts("SOURCE_SIMPLE_LOG_MAIN_IMAGE_CACHE_OFFSET_SHIM_LEVELS_AND_2048_BYTE_WIRE_BOUNDARY_OK");
    pthread_t threads[6];for(unsigned i=0;i<6;i++)assert(!pthread_create(&threads[i],NULL,worker,(void *)(uintptr_t)i));
    pid_t child = fork(); assert(child >= 0);
    if (!child) { emit(NULL,sender_uuid,dsc_uuid,0,1,"fork","child fork record"); _exit(0); }
    expected_child = child;
    unsigned seen[6]={0};
    unsigned child_records = 0;
    for(unsigned i=0;i<97;i++) {
        receive_record(buffer,&out);
        if (out.pid == child) {assert(!strcmp(out.message,"child fork record") && out.tid); child_records++;continue;}
        unsigned n,j;assert(sscanf(out.message,"thread %u record %u",&n,&j)==2 && n<6 && j<16);assert(!(seen[n]&(1u<<j)));seen[n]|=1u<<j;assert(out.tid && out.tid!=tid);
    }
    for(unsigned i=0;i<6;i++){assert(!pthread_join(threads[i],NULL));assert(seen[i]==0xffff);}
    int status; assert(child_records == 1 && waitpid(child,&status,0)==child && WIFEXITED(status) && WEXITSTATUS(status)==0);
    puts("SOURCE_SIMPLE_LOG_REAL_FORK_DURING_THREADED_LOGGING_CHILD_PID_AND_DELIVERY_OK");
    assert(!close(receiver) && !unlink(path) && !rmdir(directory));
    printf("SOURCE_SIMPLE_LOG_ACTUAL_UNIX_DATAGRAM_TRANSPORT_AND_96_CONCURRENT_RECORDS_OK %u\n",checked);
}
