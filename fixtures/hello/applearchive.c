#include <AppleArchive/AppleArchive.h>
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    AAByteStream source = AATempFileStreamOpen(), dest = AATempFileStreamOpen();
    assert(source && dest);
    assert(AAByteStreamWrite(source, "abcdef", 6) == 6);
    assert(AAByteStreamPWrite(source, "XY", 2, 2) == 2);
    assert(AAByteStreamSeek(source, 0, SEEK_CUR) == 6);
    assert(AAByteStreamSeek(source, 0, SEEK_SET) == 0);
    assert(AAByteStreamProcess(source, dest) == 6);
    char buf[7] = {0};
    assert(AAByteStreamPRead(dest, buf, 6, 0) == 6);
    assert(strcmp(buf, "abXYef") == 0);
    AAByteStreamCancel(dest);
    assert(AAByteStreamRead(dest, buf, 1) < 0 && errno == ECANCELED);
    assert(AAByteStreamClose(dest) == 0);
    assert(AAByteStreamClose(source) == 0);
    int fd = open("/dev/null", O_RDONLY);
    assert(fd >= 0);
    source = AAFileStreamOpenWithFD(fd, 0);
    assert(source && AAByteStreamClose(source) == 0);
    assert(fcntl(fd, F_GETFD) >= 0);
    close(fd);
    source = AACustomByteStreamOpen();
    assert(source && AAByteStreamRead(source, buf, 1) < 0 && errno == ENOTSUP);
    assert(AAByteStreamClose(source) == 0);
    puts("APPLEARCHIVE_FILE_STREAM_OK");
}
