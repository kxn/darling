#import <Foundation/Foundation.h>
#import <objc/runtime.h>
#include <xpc/xpc.h>
#include <dlfcn.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>

@interface NSObject (ExistingDarlingXPCPrivate)
- (void)_encodeInvocation:(NSInvocation *)invocation isReply:(BOOL)isReply into:(xpc_object_t)wire;
- (void)_startReadingFromXPCObject:(xpc_object_t)wire;
- (void)_decodeMessageFromXPCObject:(xpc_object_t)wire allowingSimpleMessageSend:(BOOL)simple
    outInvocation:(NSInvocation **)invocation outArguments:(NSArray **)arguments
    outArgumentsMaxCount:(NSUInteger)count outMethodSignature:(NSMethodSignature **)signature
    outSelector:(SEL *)selector interface:(NSXPCInterface *)interface;
@end
@protocol ScalarMessage
- (void)recordNumber:(long long)number flag:(BOOL)flag;
@end
@interface ScalarReceiver : NSObject <ScalarMessage> { @public long long number; BOOL flag; unsigned calls; }
@end
@implementation ScalarReceiver
- (void)recordNumber:(long long)value flag:(BOOL)state { number=value; flag=state; ++calls; }
@end

int main(int argc,char **argv) {
    if (argc!=2) return 2;
    @autoreleasepool {
        void *library=dlopen(argv[1],RTLD_LAZY|RTLD_LOCAL);
        if (!library) { fprintf(stderr,"%s\n",dlerror());return 3; }
        const char *names[]={"NSXPCEncoder","NSXPCDecoder"}; Class classes[2];
        for (unsigned i=0;i<2;++i) {
            char symbol[100];snprintf(symbol,sizeof(symbol),"OBJC_CLASS_$_%s",names[i]);
            classes[i]=(Class)dlsym(library,symbol);
            assert(classes[i] && classes[i]==objc_getClass(names[i]));
            snprintf(symbol,sizeof(symbol),"OBJC_METACLASS_$_%s",names[i]);
            assert((Class)dlsym(library,symbol)==object_getClass(classes[i]));
            Method method=class_getInstanceMethod(classes[i],i ? @selector(allowsKeyedCoding) : @selector(init));
            Dl_info owner;assert(method && dladdr((void *)method_getImplementation(method),&owner));
            assert(strstr(owner.dli_fname,"/runtime/native-library-stage/libFND.dylib"));
        }
        NSCoder *encoder=[classes[0] new],*decoder=[classes[1] new];
        assert(encoder.allowsKeyedCoding && decoder.allowsKeyedCoding);
        assert(encoder.requiresSecureCoding && decoder.requiresSecureCoding);
        ScalarReceiver *receiver=[ScalarReceiver new];SEL selector=@selector(recordNumber:flag:);
        NSMethodSignature *signature=[receiver methodSignatureForSelector:selector];
        NSInvocation *invocation=[NSInvocation invocationWithMethodSignature:signature];
        invocation.selector=selector;long long sent=-9223372036854775000LL;BOOL state=YES;
        [invocation setArgument:&sent atIndex:2];[invocation setArgument:&state atIndex:3];
        xpc_object_t wire=xpc_dictionary_create(NULL,NULL,0);
        [(id)encoder _encodeInvocation:invocation isReply:NO into:wire];
        xpc_object_t root=xpc_dictionary_get_value(wire,"root");
        assert(root && xpc_get_type(root)==XPC_TYPE_DATA && xpc_data_get_length(root)>8);
        assert(!memcmp(xpc_data_get_bytes_ptr(root),"bplist16",8));
        NSInvocation *decoded=nil;SEL decodedSelector=NULL;
        NSXPCInterface *interface=[NSXPCInterface interfaceWithProtocol:@protocol(ScalarMessage)];
        [(id)decoder _decodeMessageFromXPCObject:wire allowingSimpleMessageSend:NO outInvocation:&decoded
            outArguments:NULL outArgumentsMaxCount:0 outMethodSignature:NULL outSelector:&decodedSelector interface:interface];
        assert(decoded && sel_isEqual(decodedSelector,selector));
        long long number=0;BOOL flag=NO;
        [decoded getArgument:&number atIndex:2];[decoded getArgument:&flag atIndex:3];
        assert(number==sent && flag==state);
        [decoded setTarget:receiver];[decoded invoke];
        assert(receiver->calls==1 && receiver->number==sent && receiver->flag==state);
        NSCoder *bad=[classes[1] new];xpc_object_t malformed=xpc_dictionary_create(NULL,NULL,0);BOOL rejected=NO;
        @try { [(id)bad _startReadingFromXPCObject:malformed]; }
        @catch(NSException *e) { rejected=[e.name isEqualToString:NSInvalidArgumentException]; }
        assert(rejected);
        [bad release];xpc_release(malformed);[receiver release];[decoder release];[encoder release];xpc_release(wire);
        puts("EXISTING_NSXPC_CLASS_EXPORT_IDENTITIES_BPLIST16_SCALAR_INVOCATION_ROUNDTRIP_MALFORMED_REJECTION_OK");
    }
}
