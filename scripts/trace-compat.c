#include <stdint.h>

extern void _os_log_impl(void* dso, void* log, uint8_t type, const char* format,
                         uint8_t* buffer, uint32_t size);

#define LOG_ENTRY(name) \
    void name(void* dso, void* log, uint8_t type, const char* format, \
              uint8_t* buffer, uint32_t size) { \
        _os_log_impl(dso, log, type, format, buffer, size); \
    }

LOG_ENTRY(_os_log_debug_impl)
LOG_ENTRY(_os_log_error_impl)
LOG_ENTRY(_os_log_fault_impl)

// Apple Libc os/assumes.c: modern crash reporting must still terminate.
extern void _os_crash(const char* message);
extern void abort_with_payload(unsigned int name_space, uint64_t code,
                               void* payload, unsigned int payload_size,
                               const char* reason, uint64_t flags);
void _os_crash_msg(const char* format, char* message) {
    if (format) _os_crash(format);
    abort_with_payload(18, 1, 0, 0, message, 0);
    __builtin_trap();
}

// _os_log_send_and_compose_impl is supplied by the complete source libTrace
// reexport. Crash reporting above still terminates through abort_with_payload.
