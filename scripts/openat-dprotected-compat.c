#include <sys/fcntl.h>
#include <sys/types.h>
#include <stdarg.h>
#include <errno.h>

// XNU content_protection.h: DEFAULT (-1) explicitly requests traditional
// open semantics. The existing Linux-backed filesystem supplies those
// semantics; it does not supply Apple's encrypted-file protection classes.
int openat_dprotected_np(int directory,const char *path,int flags,int protection,int protectionFlags,...) {
    if ((protectionFlags&(O_DP_GETRAWENCRYPTED|O_DP_GETRAWUNENCRYPTED)) && (flags&(O_RDWR|O_WRONLY))) {
        errno=EINVAL;return -1;
    }
    if (protectionFlags || ((flags&O_CREAT) && protection!=-1)) {
        errno=ENOTSUP;return -1;
    }
    // Darling's path expander gives -1 an internal cwd meaning. POSIX openat
    // permits only AT_FDCWD as that sentinel; validate a relative-path fd
    // through the real descriptor table before entering that expander.
    // An absolute path must continue to ignore the directory argument.
    if (path && path[0]!='/' && directory!=AT_FDCWD && fcntl(directory,F_GETFD)<0)
        return -1;
    mode_t mode=0;
    if (flags&O_CREAT) {
        va_list arguments;va_start(arguments,protectionFlags);
        mode=(mode_t)va_arg(arguments,int);va_end(arguments);
    }
    return openat(directory,path,flags,mode);
}
