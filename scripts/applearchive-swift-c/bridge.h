/* C ABI declarations for the implemented stream subset. Opaque handles stay
 * private to this bridge; the public Swift wrappers retain SDK type names. */
#include <sys/types.h>
#include <stddef.h>
void *AAFileStreamOpenWithPath(const char *, int, mode_t);
void *AAFileStreamOpenWithFD(int, int);
void *AATempFileStreamOpen(void);
ssize_t AAByteStreamRead(void *, void *, size_t);
ssize_t AAByteStreamPRead(void *, void *, size_t, off_t);
ssize_t AAByteStreamWrite(void *, const void *, size_t);
ssize_t AAByteStreamPWrite(void *, const void *, size_t, off_t);
off_t AAByteStreamSeek(void *, off_t, int);
void AAByteStreamCancel(void *);
int AAByteStreamClose(void *);
off_t AAByteStreamProcess(void *, void *);
