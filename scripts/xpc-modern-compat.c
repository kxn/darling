// Convenience constructor added after Darling's baseline XPC release.
#include <stddef.h>
typedef struct _xpc_object_s *xpc_object_t;
extern xpc_object_t xpc_dictionary_create(const char *const *, const xpc_object_t *, size_t);
xpc_object_t xpc_dictionary_create_empty(void) {
    return xpc_dictionary_create(NULL,NULL,0);
}
