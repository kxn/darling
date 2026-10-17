#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>

namespace std {
inline namespace __1 {
__attribute__((noreturn, visibility("default")))
void __libcpp_verbose_abort(const char* format, ...) {
    va_list arguments;
    va_start(arguments, format);
    vfprintf(stderr, format, arguments);
    va_end(arguments);
    abort();
}
}
}
