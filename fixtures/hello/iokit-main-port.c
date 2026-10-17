#include <IOKit/IOKitLib.h>
#include <assert.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    assert(sizeof(kIOMainPortDefault) == sizeof(mach_port_t));
    assert(kIOMainPortDefault == MACH_PORT_NULL);
    assert(kIOMainPortDefault == kIOMasterPortDefault);
    Dl_info modern = {0}, legacy = {0}, matching_owner = {0};
    assert(dladdr(&kIOMainPortDefault, &modern));
    assert(dladdr(&kIOMasterPortDefault, &legacy));
    assert(dladdr((void *)IOServiceMatching, &matching_owner));
    assert(strstr(modern.dli_fname, "foundation-native-framework-stage/IOKit.framework/"));
    assert(strstr(legacy.dli_fname, "libDarlingIOKitBackend.dylib"));
    assert(strstr(matching_owner.dli_fname, "libDarlingIOKitBackend.dylib"));
    CFMutableDictionaryRef matching = IOServiceMatching("LinuxcodeSentinelProbe");
    assert(matching && CFGetTypeID(matching) == CFDictionaryGetTypeID());
    CFStringRef name = CFDictionaryGetValue(matching, CFSTR("IOProviderClass"));
    assert(name && CFEqual(name, CFSTR("LinuxcodeSentinelProbe")));
    CFRelease(matching);
    puts("IOKIT_REAL_DEFAULT_PORT_CONSTANT_AND_ORIGINAL_MATCHING_PROVIDER_OK");
    return 0;
}
