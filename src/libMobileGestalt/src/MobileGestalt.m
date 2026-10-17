/*
 This file is part of Darling.

 Copyright (C) 2019 Lubos Dolezel

 Darling is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 Darling is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with Darling.  If not, see <http://www.gnu.org/licenses/>.
*/


#include <MobileGestalt/MobileGestalt.h>
#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#import <Foundation/NSObject.h>

CFStringRef kMGQReleaseType = CFSTR("kMGQReleaseType");

extern CFDictionaryRef _CFCopySystemVersionDictionary(void);
extern CFDictionaryRef _CFCopySupplementalVersionDictionary(void) __attribute__((weak_import));
extern bool _CFMZEnabled(void) __attribute__((weak_import));

static CFStringRef copy_product_version(void)
{
    CFDictionaryRef dictionary = _CFCopySystemVersionDictionary();
    if (!dictionary) return NULL;
    CFStringRef key = _CFMZEnabled && _CFMZEnabled()
        ? CFSTR("iOSSupportVersion") : CFSTR("ProductVersion");
    CFTypeRef value = CFDictionaryGetValue(dictionary, key);
    CFStringRef answer = value && CFGetTypeID(value) == CFStringGetTypeID()
        ? (CFStringRef)CFRetain(value) : NULL;
    CFRelease(dictionary);
    return answer;
}

/* Follow the original Intel property's callback: ProductVersion from the
 * normal system dictionary, optional ProductVersionExtra from CoreFoundation's
 * supplemental dictionary, and exactly "%@ %@" when the extra value exists. */
static CFStringRef copy_human_readable_product_version(void)
{
    CFStringRef version = copy_product_version();
    if (!version) return NULL;
    CFDictionaryRef dictionary = _CFCopySupplementalVersionDictionary
        ? _CFCopySupplementalVersionDictionary() : _CFCopySystemVersionDictionary();
    CFTypeRef extra = dictionary
        ? CFDictionaryGetValue(dictionary, CFSTR("ProductVersionExtra")) : NULL;
    CFStringRef answer = extra
        ? CFStringCreateWithFormat(kCFAllocatorDefault, NULL, CFSTR("%@ %@"), version, extra)
        : (CFStringRef)CFRetain(version);
    if (dictionary) CFRelease(dictionary);
    CFRelease(version);
    return answer;
}

id MobileGestalt_copy_humanReadableProductVersionString_obj(void)
{
    /* The native wrapper tail-calls objc_autoreleaseReturnValue, despite the
     * generated C symbol containing "copy". Do not return an extra retain. */
    return [(id)copy_human_readable_product_version() autorelease];
}

static int verbose = 0;

__attribute__((constructor))
static void initme(void) {
    verbose = getenv("STUB_VERBOSE") != NULL;
}

void* MGCancelNotifications(void)
{
    if (verbose) puts("STUB: MGCancelNotifications called");
    return NULL;
}

CFStringRef MGCopyAnswer(CFStringRef key, void* unknown)
{
    if (!key || CFGetTypeID(key) != CFStringGetTypeID()) { errno = EINVAL; return NULL; }
    if (CFEqual(key, CFSTR("ProductVersion")) || CFEqual(key, CFSTR("qNNddlUK+B/YlooNoymwgA")))
        return copy_product_version();
    if (CFEqual(key, CFSTR("HumanReadableProductVersionString")) || CFEqual(key, CFSTR("ToLFRidm+eJGWnpw6W4Wwg")))
        return copy_human_readable_product_version();
    if (verbose) puts("UNSUPPORTED: MGCopyAnswer key");
    errno = ENOTSUP;
    return NULL;
}

void* MGCopyAnswerWithError(void)
{
    if (verbose) puts("STUB: MGCopyAnswerWithError called");
    return NULL;
}

void* MGCopyMultipleAnswers(void)
{
    if (verbose) puts("STUB: MGCopyMultipleAnswers called");
    return NULL;
}

void* MGGetBoolAnswer(void)
{
    if (verbose) puts("STUB: MGGetBoolAnswer called");
    return NULL;
}

void* MGGetFloat32Answer(void)
{
    if (verbose) puts("STUB: MGGetFloat32Answer called");
    return NULL;
}

void* MGGetProductType(void)
{
    if (verbose) puts("STUB: MGGetProductType called");
    return NULL;
}

void* MGGetSInt32Answer(void)
{
    if (verbose) puts("STUB: MGGetSInt32Answer called");
    return NULL;
}

void* MGGetSInt64Answer(void)
{
    if (verbose) puts("STUB: MGGetSInt64Answer called");
    return NULL;
}

void* MGGetStringAnswer(void)
{
    if (verbose) puts("STUB: MGGetStringAnswer called");
    return NULL;
}

void* MGIsDeviceOfType(void)
{
    if (verbose) puts("STUB: MGIsDeviceOfType called");
    return NULL;
}

void* MGIsDeviceOneOfType(void)
{
    if (verbose) puts("STUB: MGIsDeviceOneOfType called");
    return NULL;
}

void* MGIsQuestionValid(void)
{
    if (verbose) puts("STUB: MGIsQuestionValid called");
    return NULL;
}

void* MGRegisterForBulkUpdates(void)
{
    if (verbose) puts("STUB: MGRegisterForBulkUpdates called");
    return NULL;
}

void* MGRegisterForUpdates(void)
{
    if (verbose) puts("STUB: MGRegisterForUpdates called");
    return NULL;
}

void* MGSetAnswer(void)
{
    if (verbose) puts("STUB: MGSetAnswer called");
    return NULL;
}

void* MGSetLogHandler(void)
{
    if (verbose) puts("STUB: MGSetLogHandler called");
    return NULL;
}

void* _MGCacheCopyValueForKey(void)
{
    if (verbose) puts("STUB: _MGCacheCopyValueForKey called");
    return NULL;
}

void* _MGCacheValid(void)
{
    if (verbose) puts("STUB: _MGCacheValid called");
    return NULL;
}

void* _MGClearInProcessCache(void)
{
    if (verbose) puts("STUB: _MGClearInProcessCache called");
    return NULL;
}

void* _MGCopyDeviceDescription(void)
{
    if (verbose) puts("STUB: _MGCopyDeviceDescription called");
    return NULL;
}

void* _MGCopyIteratedDeviceDescription(void)
{
    if (verbose) puts("STUB: _MGCopyIteratedDeviceDescription called");
    return NULL;
}

void* _MGGetFastPathLog(void)
{
    if (verbose) puts("STUB: _MGGetFastPathLog called");
    return NULL;
}

void* _MGIterateDevices(void)
{
    if (verbose) puts("STUB: _MGIterateDevices called");
    return NULL;
}

void* _MGLog(void)
{
    if (verbose) puts("STUB: _MGLog called");
    return NULL;
}

void* _MGPrintIteratedDeviceDescription(void)
{
    if (verbose) puts("STUB: _MGPrintIteratedDeviceDescription called");
    return NULL;
}

void* _MGRebuildCache(void)
{
    if (verbose) puts("STUB: _MGRebuildCache called");
    return NULL;
}

void* _MGServerCopyAnswerWithError(void)
{
    if (verbose) puts("STUB: _MGServerCopyAnswerWithError called");
    return NULL;
}

void* _MGServerQuestionIsPlatform(void)
{
    if (verbose) puts("STUB: _MGServerQuestionIsPlatform called");
    return NULL;
}

void* _MGSetServer(void)
{
    if (verbose) puts("STUB: _MGSetServer called");
    return NULL;
}

void* _MGWaitForDevices(void)
{
    if (verbose) puts("STUB: _MGWaitForDevices called");
    return NULL;
}

void* _MGWriteCache(void)
{
    if (verbose) puts("STUB: _MGWriteCache called");
    return NULL;
}
