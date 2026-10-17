/* AppleArchive byte-stream subset, using the public SDK's C ABI.
 * Archive coding and compression entry points are intentionally not exported.
 */
#include <AppleArchive/AppleArchive.h>
#include <errno.h>
#include <fcntl.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <unistd.h>

struct AAByteStream_impl {
    void *data;
    AAByteStreamReadProc read;
    AAByteStreamPReadProc pread;
    AAByteStreamWriteProc write;
    AAByteStreamPWriteProc pwrite;
    AAByteStreamSeekProc seek;
    AAByteStreamCancelProc cancel;
    AAByteStreamCloseProc close;
    atomic_bool cancelled;
};

AAByteStream AACustomByteStreamOpen(void) {
    AAByteStream s = calloc(1, sizeof(*s));
    if (s) atomic_init(&s->cancelled, 0);
    return s;
}
void AACustomByteStreamSetData(AAByteStream s, void *data) { s->data = data; }
#define SETTER(Name, field, Type) \
    void AACustomByteStreamSet##Name##Proc(AAByteStream s, Type proc) { s->field = proc; }
SETTER(Read, read, AAByteStreamReadProc)
SETTER(PRead, pread, AAByteStreamPReadProc)
SETTER(Write, write, AAByteStreamWriteProc)
SETTER(PWrite, pwrite, AAByteStreamPWriteProc)
SETTER(Seek, seek, AAByteStreamSeekProc)
SETTER(Cancel, cancel, AAByteStreamCancelProc)
SETTER(Close, close, AAByteStreamCloseProc)

static int usable(AAByteStream s) {
    if (!s) { errno = EINVAL; return 0; }
    if (atomic_load(&s->cancelled)) { errno = ECANCELED; return 0; }
    return 1;
}
#define REQUIRE_OP(s, op) \
    if (!usable(s)) return -1; \
    if (!(s)->op) { errno = ENOTSUP; return -1; }
ssize_t AAByteStreamRead(AAByteStream s, void *buf, size_t count) {
    REQUIRE_OP(s, read)
    return s->read(s->data, buf, count);
}
ssize_t AAByteStreamPRead(AAByteStream s, void *buf, size_t count, off_t offset) {
    REQUIRE_OP(s, pread)
    return s->pread(s->data, buf, count, offset);
}
ssize_t AAByteStreamWrite(AAByteStream s, const void *buf, size_t count) {
    REQUIRE_OP(s, write)
    return s->write(s->data, buf, count);
}
ssize_t AAByteStreamPWrite(AAByteStream s, const void *buf, size_t count, off_t offset) {
    REQUIRE_OP(s, pwrite)
    return s->pwrite(s->data, buf, count, offset);
}
off_t AAByteStreamSeek(AAByteStream s, off_t offset, int whence) {
    REQUIRE_OP(s, seek)
    return s->seek(s->data, offset, whence);
}
void AAByteStreamCancel(AAByteStream s) {
    if (s && !atomic_exchange(&s->cancelled, 1) && s->cancel) s->cancel(s->data);
}
int AAByteStreamClose(AAByteStream s) {
    if (!s) return 0;
    int result = s->close ? s->close(s->data) : 0;
    free(s);
    return result;
}

struct FileStream { int fd; int owned; };
static ssize_t file_read(void *data, void *buf, size_t count) {
    return read(((struct FileStream *)data)->fd, buf, count);
}
static ssize_t file_pread(void *data, void *buf, size_t count, off_t offset) {
    return pread(((struct FileStream *)data)->fd, buf, count, offset);
}
static ssize_t file_write(void *data, const void *buf, size_t count) {
    return write(((struct FileStream *)data)->fd, buf, count);
}
static ssize_t file_pwrite(void *data, const void *buf, size_t count, off_t offset) {
    return pwrite(((struct FileStream *)data)->fd, buf, count, offset);
}
static off_t file_seek(void *data, off_t offset, int whence) {
    return lseek(((struct FileStream *)data)->fd, offset, whence);
}
static int file_close(void *data) {
    struct FileStream *file = data;
    int result = file->owned ? close(file->fd) : 0;
    free(file);
    return result;
}
AAByteStream AAFileStreamOpenWithFD(int fd, int automatic_close) {
    if (fcntl(fd, F_GETFD) < 0) return NULL;
    AAByteStream s = AACustomByteStreamOpen();
    if (!s) return NULL;
    struct FileStream *file = malloc(sizeof(*file));
    if (!file) { free(s); return NULL; }
    *file = (struct FileStream){ fd, automatic_close };
    s->data = file;
    s->read = file_read; s->pread = file_pread;
    s->write = file_write; s->pwrite = file_pwrite;
    s->seek = file_seek; s->close = file_close;
    return s;
}
AAByteStream AAFileStreamOpenWithPath(const char *path, int flags, mode_t mode) {
    int fd = open(path, flags, mode);
    if (fd < 0) return NULL;
    AAByteStream s = AAFileStreamOpenWithFD(fd, 1);
    if (!s) { int saved = errno; close(fd); errno = saved; }
    return s;
}
AAByteStream AATempFileStreamOpen(void) {
    char path[] = "/tmp/linuxcode-aa-XXXXXX";
    int fd = mkstemp(path);
    if (fd < 0) return NULL;
    if (unlink(path) < 0) { int saved = errno; close(fd); errno = saved; return NULL; }
    AAByteStream s = AAFileStreamOpenWithFD(fd, 1);
    if (!s) { int saved = errno; close(fd); errno = saved; }
    return s;
}
off_t AAByteStreamProcess(AAByteStream input, AAByteStream output) {
    char buf[65536];
    off_t total = 0;
    for (;;) {
        ssize_t count = AAByteStreamRead(input, buf, sizeof(buf));
        if (count < 0) return -1;
        if (!count) return total;
        for (ssize_t offset = 0; offset < count;) {
            ssize_t written = AAByteStreamWrite(output, buf + offset, count - offset);
            if (written < 0) return -1;
            if (!written) { errno = EIO; return -1; }
            offset += written;
        }
        total += count;
    }
}
