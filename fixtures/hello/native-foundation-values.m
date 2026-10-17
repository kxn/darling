#import <Foundation/Foundation.h>
#import <CoreFoundation/CoreFoundation.h>
#include <objc/runtime.h>
#include <dlfcn.h>
#include <assert.h>
#include <stdio.h>
#include <unistd.h>
#include <signal.h>
#include <sys/ucontext.h>
#include <sys/stat.h>
#include <mach/mach_vm.h>

static void phase(const char *name) { fprintf(stderr,"NATIVE_FOUNDATION_API_%s\n",name); }
static void fault(int number,siginfo_t *info,void *context) {
    ucontext_t *uc=context;uintptr_t pc=uc->uc_mcontext->__ss.__rip;
    Dl_info image={0};dladdr((void *)pc,&image);
    fprintf(stderr,"NATIVE_FOUNDATION_FAULT signal=%d address=%p pc=%p image=%s offset=%#lx\n",
        number,info->si_addr,(void *)pc,image.dli_fname?image.dli_fname:"?",pc-(uintptr_t)image.dli_fbase);
    fprintf(stderr,"NATIVE_FOUNDATION_REGS rbp=%#llx rsp=%#llx rdi=%#llx rsi=%#llx rax=%#llx rbx=%#llx\n",
        uc->uc_mcontext->__ss.__rbp,uc->uc_mcontext->__ss.__rsp,
        uc->uc_mcontext->__ss.__rdi,uc->uc_mcontext->__ss.__rsi,
        uc->uc_mcontext->__ss.__rax,uc->uc_mcontext->__ss.__rbx);
    uintptr_t fp=uc->uc_mcontext->__ss.__rbp;
    for(unsigned i=0;i<24 && fp;i++) {
        uintptr_t pair[2];mach_vm_size_t bytes=0;
        if(mach_vm_read_overwrite(mach_task_self(),fp,sizeof(pair),(mach_vm_address_t)pair,&bytes)!=KERN_SUCCESS || bytes!=sizeof(pair))break;
        Dl_info frame={0};dladdr((void *)pair[1],&frame);
        fprintf(stderr,"NATIVE_FOUNDATION_FRAME %u pc=%p image=%s offset=%#lx\n",i,(void *)pair[1],
            frame.dli_fname?frame.dli_fname:"?",pair[1]-(uintptr_t)frame.dli_fbase);
        uintptr_t next=pair[0]&UINT64_C(0x0fffffffffffffff);
        if(next<=fp || next-fp>1024*1024 || next&15)break;
        fp=next;
    }
    _exit(128+number);
}
static void owner(Class cls,SEL selector,BOOL meta) {
    Method method=meta?class_getClassMethod(cls,selector):class_getInstanceMethod(cls,selector);
    assert(method);Dl_info info;assert(dladdr((void *)method_getImplementation(method),&info));
    assert(strstr(info.dli_fname,"foundation-native-framework-stage"));
}
int main(void) {
    phase("MAIN_ENTERED");
    struct sigaction action={0};action.sa_sigaction=fault;action.sa_flags=SA_SIGINFO;
    sigemptyset(&action.sa_mask);
    sigaction(SIGSEGV,&action,NULL);sigaction(SIGBUS,&action,NULL);
    sigaction(SIGILL,&action,NULL);sigaction(SIGABRT,&action,NULL);
    uintptr_t *tagged_mask=dlsym(RTLD_DEFAULT,"objc_debug_taggedpointer_mask");
    assert(tagged_mask && *tagged_mask==0);
    @autoreleasepool {
        phase("STRINGS");
        owner([NSString class],@selector(stringWithFormat:),YES);
        NSString *s=[NSString stringWithFormat:@"%@-%d",@"中文",42];
        assert([s isEqualToString:@"中文-42"]);
        NSMutableString *mutable=[s mutableCopy];[mutable appendString:@"!"];
        assert([s isEqualToString:@"中文-42"] && [mutable isEqualToString:@"中文-42!"]);
        NSData *utf8=[s dataUsingEncoding:NSUTF8StringEncoding];
        assert([[[NSString alloc] initWithData:utf8 encoding:NSUTF8StringEncoding] isEqualToString:s]);
        phase("COLLECTIONS");
        NSMutableArray *array=[NSMutableArray arrayWithObjects:@1,@2,@3,nil];
        [array addObject:@4];assert([array count]==4 && [[array objectAtIndex:3] intValue]==4);
        NSArray *copy=[array copy];[array removeLastObject];assert([copy count]==4 && [array count]==3);
        NSDictionary *dictionary=@{@"文字":s,@"numbers":copy};
        assert([[dictionary objectForKey:@"文字"] isEqualToString:s]);
        NSSet *set=[NSSet setWithArray:@[@1,@2,@1]];assert([set count]==2);
        phase("JSON");
        NSError *error=nil;
        NSData *json=[NSJSONSerialization dataWithJSONObject:dictionary options:0 error:&error];assert(json && !error);
        NSDictionary *decoded=[NSJSONSerialization JSONObjectWithData:json options:0 error:&error];
        assert(!error && [decoded isEqualToDictionary:dictionary]);
        assert(![NSJSONSerialization JSONObjectWithData:[@"{" dataUsingEncoding:NSUTF8StringEncoding] options:0 error:&error] && error);
        phase("DATE_AND_ERROR");
        NSDate *date=[NSDate dateWithTimeIntervalSince1970:12345.25];assert([date timeIntervalSince1970]==12345.25);
        NSError *value=[NSError errorWithDomain:@"linuxcode.test" code:42 userInfo:@{NSLocalizedDescriptionKey:s}];
        assert([value code]==42 && [[value localizedDescription] isEqualToString:s]);
        phase("COREFOUNDATION");
        CFStringRef string=CFStringCreateWithCString(NULL,"native-CF",kCFStringEncodingUTF8);
        assert(string && CFStringGetLength(string)==9 && CFGetTypeID(string)==CFStringGetTypeID());
        CFMutableDictionaryRef table=CFDictionaryCreateMutable(NULL,0,&kCFTypeDictionaryKeyCallBacks,&kCFTypeDictionaryValueCallBacks);
        CFDictionarySetValue(table,string,CFSTR("value"));assert(CFEqual(CFDictionaryGetValue(table,string),CFSTR("value")));
        CFRelease(table);CFRelease(string);
        phase("FILES");
        char pattern[]="/tmp/linuxcode-native-foundation-XXXXXX";char *directory=mkdtemp(pattern);assert(directory);
        NSString *path=[[NSString stringWithUTF8String:directory] stringByAppendingPathComponent:@"中文.txt"];
        error=nil;BOOL written=[s writeToFile:path atomically:YES encoding:NSUTF8StringEncoding error:&error];
        if(!written)fprintf(stderr,"NATIVE_FOUNDATION_FILE_WRITE_FAILED domain=%s code=%ld description=%s\n",
            [[error domain] UTF8String],(long)[error code],[[error description] UTF8String]);
        assert(written && !error);
        assert([[NSString stringWithContentsOfFile:path encoding:NSUTF8StringEncoding error:&error] isEqualToString:s] && !error);
        assert(!chmod([path fileSystemRepresentation],0640));
        NSString *replacement=@"覆盖内容-43";
        assert([replacement writeToFile:path atomically:YES encoding:NSUTF8StringEncoding error:&error] && !error);
        assert([[NSString stringWithContentsOfFile:path encoding:NSUTF8StringEncoding error:&error] isEqualToString:replacement] && !error);
        struct stat resulting;assert(!stat([path fileSystemRepresentation],&resulting));
        // The documented NSData atomic-write contract replaces the file; it
        // does not promise preservation of the previous file's attributes.
        fprintf(stderr,"NATIVE_FOUNDATION_ATOMIC_OVERWRITE_PERMISSION_BITS=%#o\n",resulting.st_mode&0777);
        assert([[NSFileManager defaultManager] removeItemAtPath:path error:&error] && !error);
        assert(!rmdir(directory));
        [copy release];[mutable release];
    }
    puts("NATIVE_FOUNDATION_STRINGS_COLLECTIONS_JSON_DATE_ERROR_CF_AND_FILES_OK");
    return 0;
}
