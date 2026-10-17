/*
 * This file is part of Darling, licensed under GPL-3.0-or-later.
 *
 * MobileAsset's Pallas query is a synchronous service operation. Its return
 * value is a response code; the boolean state is a separate output argument.
 * This implements the client protocol, not the MobileAsset download daemon.
 */
#import <MobileAsset/MobileAsset.h>
#include <mach/mach.h>
#include <servers/bootstrap.h>
#include <stdlib.h>
#include <uuid/uuid.h>
#include <xpc/xpc.h>

static const char* const pallasService = "com.apple.mobileassetd.v2";

static xpc_object_t createPallasRequest(NSString* assetType, int64_t action)
{
    xpc_object_t request = xpc_dictionary_create(NULL, NULL, 0);
    if (!request) return NULL;
    if ([assetType isKindOfClass:[NSString class]])
        xpc_dictionary_set_string(request, "AssetType", [assetType UTF8String]);
    xpc_dictionary_set_int64(request, "messageAction", action);
    return request;
}

/* Returns an owned reply or NULL. The status is independent of any payload. */
static xpc_object_t sendPallasRequest(xpc_object_t request, int64_t* result)
{
    *result = 1;
    if (!request) return NULL;
    @autoreleasepool {
        NSString* clientName = [[NSBundle mainBundle] bundleIdentifier];
        if (!clientName) clientName = [NSString stringWithFormat:@"%s", getprogname()];
        if (!clientName) clientName = @"UnknownClient";
        xpc_dictionary_set_string(request, "clientName", [clientName UTF8String]);
        xpc_dictionary_set_string(request, "requestType", "requestTypeSync");

        for (unsigned attempt = 0; attempt < 2; ++attempt) {
            /* A real bootstrap lookup also avoids waiting on an unconnected
             * channel in Darling's old XPC backend when the service is absent.
             * A missing service is an operation failure, never 'disabled/OK'. */
            mach_port_t port = MACH_PORT_NULL;
            if (bootstrap_look_up(bootstrap_port, (char*)pallasService, &port) != KERN_SUCCESS)
                break;
            mach_port_deallocate(mach_task_self(), port);
            xpc_connection_t connection = xpc_connection_create(pallasService, NULL);
            if (!connection) break;
            uuid_t identifier; char text[37];
            uuid_generate(identifier); uuid_unparse_upper(identifier, text);
            xpc_dictionary_set_string(request, "connectionIdentifier", text);
            xpc_connection_set_event_handler(connection, ^(xpc_object_t event) { (void)event; });
            xpc_connection_resume(connection);
            xpc_object_t reply = xpc_connection_send_message_with_reply_sync(connection, request);
            bool retry = reply == XPC_ERROR_CONNECTION_INTERRUPTED && attempt == 0;
            if (reply && xpc_get_type(reply) == XPC_TYPE_DICTIONARY) {
                *result = xpc_dictionary_get_int64(reply, "Result");
                xpc_connection_cancel(connection);
                xpc_release(connection);
                return reply;
            }
            if (reply) xpc_release(reply);
            xpc_connection_cancel(connection);
            xpc_release(connection);
            if (!retry) break;
        }
        return NULL;
    }
}

static int64_t sendPallasStatus(xpc_object_t request)
{
    int64_t result;
    xpc_object_t reply = sendPallasRequest(request, &result);
    if (reply) xpc_release(reply);
    if (request) xpc_release(request);
    return result;
}

int64_t _MAsendGetPallasEnabled(NSString* assetType, bool* enabled)
{
    if (enabled) *enabled = false;
    @autoreleasepool {
        xpc_object_t request = createPallasRequest(assetType, 32);
        int64_t result;
        xpc_object_t reply = sendPallasRequest(request, &result);
        if (result == 0 && enabled) *enabled = xpc_dictionary_get_bool(reply, "pallasEnabled");
        if (reply) xpc_release(reply);
        if (request) xpc_release(request);
        return result;
    }
}

int64_t MAGetPallasEnabled(NSString* assetType, bool* enabled)
{
    bool value = true;
    int64_t result = _MAsendGetPallasEnabled(assetType, &value);
    if (enabled) *enabled = value;
    return result;
}

int64_t _MAsendSetPallasEnabled(NSString* assetType, bool enabled)
{
    @autoreleasepool {
        xpc_object_t request = createPallasRequest(assetType, 33);
        if (request) xpc_dictionary_set_bool(request, "pallasEnabled", enabled);
        return sendPallasStatus(request);
    }
}

int64_t MASetPallasEnabled(NSString* assetType, BOOL enabled)
{
    return _MAsendSetPallasEnabled(assetType, enabled != NO);
}

NSString* _MAsendGetPallasAudience(NSString* assetType)
{
    NSString* audience = nil;
    @autoreleasepool {
        xpc_object_t request = createPallasRequest(assetType, 20);
        /* The native getter returns an empty constant on allocation failure,
         * but nil on a service error or absent/wrongly typed audience field. */
        if (!request) return @"";
        int64_t result;
        xpc_object_t reply = sendPallasRequest(request, &result);
        if (result == 0) {
            const char* text = xpc_dictionary_get_string(reply, "pallasAudience");
            if (text) audience = [[NSString alloc] initWithUTF8String:text];
        }
        if (reply) xpc_release(reply);
        xpc_release(request);
    }
    return [audience autorelease];
}

NSString* MAGetPallasAudience(NSString* assetType)
{
    return _MAsendGetPallasAudience(assetType);
}

int64_t _MAsendSetPallasAudience(NSString* audience, NSString* assetType)
{
    @autoreleasepool {
        if (audience && ![audience isKindOfClass:[NSString class]]) return 1;
        xpc_object_t request = createPallasRequest(assetType, 10);
        if (request && audience)
            xpc_dictionary_set_string(request, "pallasAudience", [audience UTF8String]);
        return sendPallasStatus(request);
    }
}

int64_t MASetPallasAudienceForType(NSString* audience, NSString* assetType)
{
    return _MAsendSetPallasAudience(audience, assetType);
}

int64_t MASetPallasAudience(NSString* audience)
{
    return _MAsendSetPallasAudience(audience, nil);
}

int64_t _MAsendSetPallasUrlForType(NSURL* url, NSString* assetType)
{
    @autoreleasepool {
        xpc_object_t request = createPallasRequest(assetType, 9);
        if (!request) return 1;
        if (url) {
            if (![url isKindOfClass:[NSURL class]]) {
                xpc_release(request);
                return 5;
            }
            xpc_dictionary_set_string(request, "pallasUrl", [[url absoluteString] UTF8String]);
        } else {
            xpc_dictionary_set_bool(request, "serverOverrideClear", true);
        }
        return sendPallasStatus(request);
    }
}

int64_t _MAsendSetPallasUrl(NSURL* url)
{
    return _MAsendSetPallasUrlForType(url, nil);
}

int64_t MASetPallasUrlForType(NSURL* url, NSString* assetType)
{
    return _MAsendSetPallasUrlForType(url, assetType);
}

int64_t MASetPallasUrl(NSURL* url)
{
    return _MAsendSetPallasUrlForType(url, nil);
}
