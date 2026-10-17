#include <CoreGraphics/CGDisplayConfiguration.h>
#include <CoreGraphics/CGError.h>
#include <IOKit/IOKitLib.h>
#include <assert.h>
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

extern CGError CGSAcceleratorForDisplayNumber(CGDirectDisplayID, io_service_t *, uint32_t *);

int main(void) {
    setbuf(stdout, NULL);
    Dl_info query = {0}, display = {0};
    assert(dladdr((void *)CGSAcceleratorForDisplayNumber, &query));
    assert(dladdr((void *)CGDisplayIOServicePort, &display));
    assert(strstr(query.dli_fname, "foundation-native-framework-stage/CoreGraphics.framework/"));
    assert(strstr(display.dli_fname, "libDarlingCoreGraphicsBackend.dylib"));
    uint32_t displays[] = {0, 1, UINT32_MAX};
    for (unsigned i = 0; i < sizeof(displays)/sizeof(displays[0]); ++i) {
        io_service_t framebuffer = CGDisplayIOServicePort(displays[i]);
        printf("CGS_HEADLESS_ORIGINAL_DISPLAY_QUERY=%u FRAMEBUFFER=%u\n", displays[i], framebuffer);
        // This fixture verifies the actual no-device path of this environment.
        // A future environment with devices needs separate hardware validation.
        assert(framebuffer == MACH_PORT_NULL);
        io_service_t accelerator = 123;
        uint32_t index = 123;
        CGError result = CGSAcceleratorForDisplayNumber(displays[i], &accelerator, &index);
        assert(result == kCGErrorFailure && accelerator == MACH_PORT_NULL && index == 0);
    }
    puts("CGS_ACCELERATOR_PRODUCTION_REAL_BACKEND_NO_DISPLAY_FAILURE_AND_PROVIDER_OK");
    return 0;
}
