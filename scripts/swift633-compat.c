// Swift 5.2 BackDeployment.cpp exported this for non-OS runtimes. Old Darwin
// Foundation overlays still import it. Read the actual Objective-C ABI mask.
#include <stdint.h>
extern const uintptr_t objc_debug_swift_stable_abi_bit;
unsigned long long _swift_classIsSwiftMask = 2;
__attribute__((constructor)) static void initialize_legacy_swift_mask(void) {
    _swift_classIsSwiftMask = objc_debug_swift_stable_abi_bit;
}
