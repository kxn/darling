#import <DiskManagement/DiskManagement.h>

// Verified against the original Intel DiskManagement cache function:
// push rbp; mov rsp,rbp; xor eax,eax; pop rbp; ret.
// See artifacts/diskmanagement-nserror-native-reference.json in the host
// experiment. No NSError or disk-operation success is manufactured here.
NSError *DMNSError(void)
{
    return nil;
}
