#include <CoreFoundation/CoreFoundation.h>
// Existing Darling AppKit uses this legacy ImageIO key. Preserve its value;
// modern native ImageIO does not implement the old Darling DPI option.
const CFStringRef kCGImageDestinationDPI = CFSTR("kCGImageDestinationDPI");
