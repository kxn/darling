/* Reconstructed from the original x86_64 SoftLinking control flow: try a
 * null-terminated path list with RTLD_LAZY|RTLD_LOCAL and preserve the caller
 * for @rpath resolution. On failure optionally return malloc-owned dlerrors.
 */
#include <dlfcn.h>
#include <errno.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

extern void *dlopen_from(const char *, int, const void *);

static void *open_paths(const char *const *paths, char **error_message, const void *caller) {
    char *errors = NULL;
    size_t used = 0;
    if (paths) for (size_t i = 0; paths[i]; ++i) {
        void *image = dlopen_from(paths[i], RTLD_LAZY | RTLD_LOCAL, caller);
        if (image) { free(errors); return image; }
        const char *message = dlerror();
        if (!error_message) continue;
        if (!message) message = "dlopen failed without an error message";
        size_t length = strlen(message);
        if (used > SIZE_MAX - 2 || length > SIZE_MAX - used - 2) {
            free(errors); *error_message = NULL; errno = ENOMEM; return NULL;
        }
        char *expanded = realloc(errors, used + length + 2);
        if (!expanded) { free(errors); *error_message = NULL; return NULL; }
        errors = expanded;
        if (used) errors[used++] = '\n';
        memcpy(errors + used, message, length + 1);
        used += length;
    }
    if (error_message) *error_message = errors ? errors : strdup("");
    else free(errors);
    return NULL;
}

void *_sl_dlopen(const char *const *paths, char **error_message) {
    return open_paths(paths, error_message, __builtin_return_address(0));
}
void *_sl_dlopen_audited(const char *const *paths) {
    return open_paths(paths, NULL, __builtin_return_address(0));
}
