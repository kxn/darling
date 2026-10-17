#import <Foundation/Foundation.h>
#import <Foundation/NSSpellEngine.h>
#include <objc/runtime.h>
#include <dlfcn.h>
#include <assert.h>
#include <stdio.h>
#include <signal.h>
#include <sys/ucontext.h>
#include <mach/mach_vm.h>
#include <unistd.h>
static void fault(int number,siginfo_t *info,void *context) {
    ucontext_t *uc=context;uintptr_t pc=uc->uc_mcontext->__ss.__rip,fp=uc->uc_mcontext->__ss.__rbp;
    Dl_info image={0};dladdr((void *)pc,&image);
    fprintf(stderr,"LEGACY_FOUNDATION_FAULT signal=%d address=%p pc=%p image=%s offset=%#lx\n",
        number,info->si_addr,(void *)pc,image.dli_fname?image.dli_fname:"?",pc-(uintptr_t)image.dli_fbase);
    fprintf(stderr,"LEGACY_FOUNDATION_REGS rdi=%#llx rsi=%#llx rax=%#llx\n",
        uc->uc_mcontext->__ss.__rdi,uc->uc_mcontext->__ss.__rsi,uc->uc_mcontext->__ss.__rax);
    for(unsigned i=0;i<20 && fp;i++) {
        uintptr_t pair[2];mach_vm_size_t bytes=0;
        if(mach_vm_read_overwrite(mach_task_self(),fp,sizeof(pair),(mach_vm_address_t)pair,&bytes)!=KERN_SUCCESS || bytes!=sizeof(pair))break;
        Dl_info frame={0};dladdr((void *)pair[1],&frame);
        fprintf(stderr,"LEGACY_FOUNDATION_FRAME %u image=%s offset=%#lx\n",i,
            frame.dli_fname?frame.dli_fname:"?",pair[1]-(uintptr_t)frame.dli_fbase);
        uintptr_t next=pair[0]&UINT64_C(0x0fffffffffffffff);if(next<=fp || next-fp>1024*1024 || next&15)break;fp=next;
    }
    _exit(128+number);
}
extern NSString *const NSPlatformResourceNameSuffix;
@interface DelegateProbe : NSSpellEngine
@end
@implementation DelegateProbe
- (NSRange)checkGrammarInString:(NSString *)text language:(NSString *)language details:(NSArray **)details {
    assert([text isEqualToString:@"中文"] && [language isEqualToString:@"test"]);
    if(details)*details=@[@{ @"actual":text }];return NSMakeRange(7,2);
}
- (NSArray *)suggestGuessesForWord:(NSString *)word inLanguage:(NSString *)language {
    return @[word,language];
}
@end
int main(void) {
    struct sigaction action={0};action.sa_sigaction=fault;action.sa_flags=SA_SIGINFO;sigemptyset(&action.sa_mask);
    sigaction(SIGSEGV,&action,NULL);sigaction(SIGBUS,&action,NULL);sigaction(SIGILL,&action,NULL);sigaction(SIGABRT,&action,NULL);
    fputs("LEGACY_FOUNDATION_MAIN_ENTERED\n",stderr);
    @autoreleasepool {
        assert([NSPlatformResourceNameSuffix isEqualToString:@"darwin"]);
        fputs("LEGACY_FOUNDATION_SUFFIX_OK\n",stderr);
        assert(class_getSuperclass([NSSpellEngine class])==[NSObject class]);
        assert(class_getInstanceSize([NSSpellEngine class])==class_getInstanceSize([NSObject class]));
        Method method=class_getClassMethod([NSSpellEngine class],@selector(allSpellEngines));
        Dl_info info;assert(dladdr((void *)method_getImplementation(method),&info));
        assert(strstr(info.dli_fname,"libDarlingLegacyFoundation.dylib"));
        NSArray *engines=[NSSpellEngine allSpellEngines];assert(engines && [engines isKindOfClass:[NSArray class]]);
        fputs("LEGACY_FOUNDATION_REGISTRY_OK\n",stderr);
        assert([NSSpellEngine spellEngines]==nil);
        DelegateProbe *probe=[[DelegateProbe alloc] init];NSArray *details=nil;
        // The engine never dereferences the delegate's sender parameter.
        // Allocation supplies its actual type without starting a server.
        NSSpellServer *server=[NSSpellServer alloc];
        NSRange range=[probe spellServer:server checkGrammarInString:@"中文" language:@"test" details:&details];
        assert(range.location==7 && range.length==2 && [details count]==1);
        assert(([[probe spellServer:server suggestGuessesForWord:@"word" inLanguage:@"test"] isEqualToArray:@[@"word",@"test"]]));
        [server release];
        [probe release];
        NSSpellEngine *abstract=[[NSSpellEngine alloc] init];BOOL rejected=NO;
        @try { [abstract suggestGuessesForWord:@"word" inLanguage:@"test"]; }
        @catch(NSException *error) {
            rejected=[[error name] isEqualToString:NSInternalInconsistencyException] &&
                [[error reason] rangeOfString:@"unavailable"].location!=NSNotFound;
        }
        assert(rejected);[abstract release];
    }
    puts("LEGACY_FOUNDATION_REAL_SUFFIX_REGISTRY_DELEGATION_AND_UNSUPPORTED_EXCEPTION_OK");return 0;
}
