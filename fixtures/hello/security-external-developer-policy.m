#import <Foundation/Foundation.h>
#include <CoreFoundation/CoreFoundation.h>
#include <Security/Security.h>
#include <assert.h>
#include <dlfcn.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
extern SecPolicyRef SecPolicyCreateAppleExternalDeveloper(void);
typedef SecPolicyRef (*Create)(bool);
typedef CFDictionaryRef (*Options)(SecPolicyRef);
typedef CFStringRef (*GetString)(SecPolicyRef);
typedef void (*SetOption)(SecPolicyRef,CFStringRef,CFTypeRef);
static Create create;
static Options options;
static CFTypeID policyType;
static int number(CFTypeRef value) {
    assert(value && CFGetTypeID(value)==CFNumberGetTypeID());int result;
    assert(CFNumberGetValue(value,kCFNumberIntType,&result));return result;
}
static void oidArray(CFDictionaryRef dict,CFStringRef key,const char** expected,unsigned count) {
    CFArrayRef array=CFDictionaryGetValue(dict,key);
    assert(array && CFGetTypeID(array)==CFArrayGetTypeID() && CFArrayGetCount(array)==count);
    for(unsigned i=0;i<count;++i) {
        CFStringRef text=CFStringCreateWithCString(NULL,expected[i],kCFStringEncodingUTF8);
        assert(CFEqual(CFArrayGetValueAtIndex(array,i),text));CFRelease(text);
    }
}
static void inspect(SecPolicyRef policy,bool expiry) {
    assert(policy && CFGetTypeID(policy)==policyType);
    CFDictionaryRef dict=options(policy);
    assert(dict && CFGetTypeID(dict)==CFDictionaryGetTypeID() && CFDictionaryGetCount(dict)==(expiry?18:15));
    CFStringRef checks[]={CFSTR("CriticalExtensions"),CFSTR("UnparseableExtension"),CFSTR("DuplicateExtension"),
        CFSTR("IdLinkage"),CFSTR("BasicConstraints"),CFSTR("NonEmptySubject"),CFSTR("WeakKeySize"),CFSTR("WeakSignature")};
    for(unsigned i=0;i<8;++i)assert(CFDictionaryGetValue(dict,checks[i])==kCFBooleanTrue);
    CFStringRef temporal[]={CFSTR("TemporalValidity"),CFSTR("BlackListedLeaf"),CFSTR("GrayListedLeaf")};
    for(unsigned i=0;i<3;++i)assert(expiry?CFDictionaryGetValue(dict,temporal[i])==kCFBooleanTrue:!CFDictionaryContainsKey(dict,temporal[i]));
    CFDictionaryRef anchor=CFDictionaryGetValue(dict,CFSTR("AnchorApple"));
    assert(anchor && CFGetTypeID(anchor)==CFDictionaryGetTypeID() && !CFDictionaryGetCount(anchor));
    assert(number(CFDictionaryGetValue(dict,CFSTR("ChainLength")))==3);
    const char* intermediate[]={"1.2.840.113635.100.6.2.1","1.2.840.113635.100.6.2.6"};
    oidArray(dict,CFSTR("IntermediateMarkerOid"),intermediate,2);
    const char* leaf[]={"1.2.840.113635.100.6.1.2","1.2.840.113635.100.6.1.4","1.2.840.113635.100.6.1.5",
        "1.2.840.113635.100.6.1.7","1.2.840.113635.100.6.1.8","1.2.840.113635.100.6.1.12",
        "1.2.840.113635.100.6.1.13","1.2.840.113635.100.6.1.14","1.2.840.113635.100.6.1.35"};
    oidArray(dict,CFSTR("LeafMarkerOid"),leaf,9);
    const char* eku[]={"1.3.6.1.5.5.7.3.3","1.2.840.113635.100.4.8","1.2.840.113635.100.4.9","1.2.840.113635.100.4.13"};
    oidArray(dict,CFSTR("ExtendedKeyUsage"),eku,4);
    assert(CFEqual(CFDictionaryGetValue(dict,CFSTR("Revocation")),CFSTR("AnyRevocationMethod")));
    CFDictionaryRef sizes=CFDictionaryGetValue(dict,CFSTR("KeySize"));
    assert(sizes && CFGetTypeID(sizes)==CFDictionaryGetTypeID() && CFDictionaryGetCount(sizes)==2);
    assert(number(CFDictionaryGetValue(sizes,kSecAttrKeyTypeRSA))==2048);
    assert(number(CFDictionaryGetValue(sizes,kSecAttrKeyTypeECSECPrimeRandom))==256);
}
static void* worker(void* context) {
    unsigned thread=(unsigned)(uintptr_t)context;
    @autoreleasepool {
        for(unsigned i=0;i<16;++i) {bool expiry=(thread+i)%2;SecPolicyRef p=create(expiry);inspect(p,expiry);CFRelease(p);}
    }
    return NULL;
}
int main(int argc,char** argv) {
    assert(argc==4);setbuf(stdout,NULL);
    void* h=dlopen(argv[1],RTLD_LAZY|RTLD_LOCAL);
    if(!h)fprintf(stderr,"%s\n",dlerror());assert(h);
    create=dlsym(h,"SecPolicyCreateAppleExternalDeveloperOptionalExpiry");
    options=dlsym(h,"SecPolicyGetOptions");
    GetString oid=dlsym(h,"SecPolicyGetOidString"),name=dlsym(h,"SecPolicyGetName");
    SetOption set=dlsym(h,"SecPolicySetOptionsValue");
    assert(create && options && oid && name && set);
    Dl_info impl,base,factory;assert(dladdr((void*)create,&impl) && dladdr((void*)options,&base));
    void* realFactory=dlsym(h,"SecPolicyCreate");assert(realFactory && dladdr(realFactory,&factory));
    assert(!strcmp(impl.dli_fname,argv[2]) && !strcmp(base.dli_fname,argv[1]) && base.dli_fbase==factory.dli_fbase);
    assert(dladdr((void*)SecPolicyGetTypeID,&factory) && factory.dli_fbase==base.dli_fbase);
    policyType=SecPolicyGetTypeID();assert(policyType);
    puts("SOURCE_SECURITY_POLICY_NEW_FUNCTION_REAL_BASE_FACTORY_AND_EXISTING_ACCESSOR_OWNERS_OK");
    SecPolicyRef withExpiry,withoutExpiry,same;
    @autoreleasepool {withExpiry=create(true);withoutExpiry=create(false);same=create(true);}
    inspect(withExpiry,true);inspect(withoutExpiry,false);inspect(same,true);
    assert(CFEqual(withExpiry,same) && CFHash(withExpiry)==CFHash(same) && !CFEqual(withExpiry,withoutExpiry));
    assert(CFEqual(oid(withExpiry),CFSTR("1.2.840.113635.100.1.65")) && CFEqual(name(withExpiry),CFSTR("Developer")));
    CFDictionaryRef properties=SecPolicyCopyProperties(withExpiry);assert(properties);
    assert(CFEqual(CFDictionaryGetValue(properties,kSecPolicyOid),CFSTR("1.2.840.113635.100.1.65")));CFRelease(properties);
    puts("SOURCE_SECURITY_POLICY_TRUE_FALSE_ALL_18_15_TYPED_CONSTRAINTS_OIDS_EKU_ROOT_CHAIN_REVOCATION_KEY_SIZES_OK");
    SecPolicyRef old=SecPolicyCreateAppleExternalDeveloper();assert(old);
    CFMutableDictionaryRef normalized=CFDictionaryCreateMutableCopy(NULL,0,options(old));assert(normalized);
    CFDictionarySetValue(normalized,CFSTR("UnparseableExtension"),kCFBooleanTrue);
    CFDictionarySetValue(normalized,CFSTR("DuplicateExtension"),kCFBooleanTrue);
    CFMutableArrayRef leaf=CFArrayCreateMutableCopy(NULL,0,CFDictionaryGetValue(normalized,CFSTR("LeafMarkerOid")));assert(leaf);
    CFArrayAppendValue(leaf,CFSTR("1.2.840.113635.100.6.1.35"));
    CFDictionarySetValue(normalized,CFSTR("LeafMarkerOid"),leaf);CFRelease(leaf);
    if(!CFEqual(normalized,options(withExpiry))) {CFShow(normalized);CFShow(options(withExpiry));}
    assert(CFEqual(normalized,options(withExpiry)));CFRelease(normalized);CFRelease(old);
    CFMutableDictionaryRef noExpiry=CFDictionaryCreateMutableCopy(NULL,0,options(withExpiry));assert(noExpiry);
    CFDictionaryRemoveValue(noExpiry,CFSTR("TemporalValidity"));CFDictionaryRemoveValue(noExpiry,CFSTR("BlackListedLeaf"));
    CFDictionaryRemoveValue(noExpiry,CFSTR("GrayListedLeaf"));assert(CFEqual(noExpiry,options(withoutExpiry)));CFRelease(noExpiry);
    puts("SOURCE_SECURITY_POLICY_REAL_LEGACY_FACTORY_DIFFERENTIAL_AND_EXACT_EXPIRY_MODE_DELTA_OK");
    @autoreleasepool {
        NSData* data=[NSData dataWithContentsOfFile:[NSString stringWithUTF8String:argv[3]]];assert(data);
        SecCertificateRef cert=SecCertificateCreateWithData(NULL,(CFDataRef)data);assert(cert);
        SecTrustRef trust=NULL;assert(SecTrustCreateWithCertificates(cert,withExpiry,&trust)==errSecSuccess && trust);
        assert(CFGetTypeID(trust)==SecTrustGetTypeID());CFArrayRef policies=NULL;
        assert(SecTrustCopyPolicies(trust,&policies)==errSecSuccess && policies && CFArrayGetCount(policies)==1);
        assert(CFEqual(CFArrayGetValueAtIndex(policies,0),withExpiry));CFRelease(policies);CFRelease(trust);CFRelease(cert);
    }
    puts("SOURCE_SECURITY_POLICY_GENUINE_CERTIFICATE_AND_TRUST_CONTAINER_ACCEPT_NEW_POLICY_NO_TRUST_EVALUATION_CLAIM_OK");
    set(withExpiry,CFSTR("CallerOnlyMutation"),CFSTR("one"));
    assert(CFDictionaryContainsKey(options(withExpiry),CFSTR("CallerOnlyMutation")) && !CFDictionaryContainsKey(options(same),CFSTR("CallerOnlyMutation")));
    CFRelease(withExpiry);CFRelease(withoutExpiry);CFRelease(same);
    pthread_t threads[8];
    for(unsigned i=0;i<8;++i)assert(!pthread_create(&threads[i],NULL,worker,(void*)(uintptr_t)i));
    for(unsigned i=0;i<8;++i)assert(!pthread_join(threads[i],NULL));
    puts("SOURCE_SECURITY_POLICY_OWNED_LIFETIME_MUTATION_ISOLATION_AND_EIGHT_THREADS_128_REAL_OBJECTS_OK");
    return 0;
}
