/* Keep the actual legacy declarations/layouts. Only the old availability
 * annotations need isolation from the newer public SDK's removed platforms. */
#include <Availability.h>
#pragma push_macro("__API_UNAVAILABLE")
#undef __API_UNAVAILABLE
#define __API_UNAVAILABLE(...)
#include "../vendor/darling/src/external/dyld/include/mach-o/dyld_process_info.h"
#pragma pop_macro("__API_UNAVAILABLE")
