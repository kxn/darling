#include <CoreUtils/CryptoUtils.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
static unsigned checks,cases;
#define CHECK(x) do{++checks;if(!(x)){fprintf(stderr,"FAIL case=%u line=%d %s\n",cases,__LINE__,#x);exit(1);}}while(0)
static unsigned char *load(FILE *f,size_t n){unsigned char *p=malloc(n?n:1);CHECK(p);CHECK(fread(p,1,n,f)==n);return p;}
int main(int argc,char **argv){
    CHECK(argc==2);setbuf(stdout,NULL);
    const CryptoHashDescriptor *descriptors[]={kCryptoHashDescriptor_SHA1,kCryptoHashDescriptor_SHA256,kCryptoHashDescriptor_SHA512};
    Dl_info owner;CHECK(dladdr((void*)CryptoHashOneShot,&owner));CHECK(strstr(owner.dli_fname,"/coreutils-crypto-source/frameworks/CoreUtils.framework/"));
    CHECK(dladdr((void*)CC_SHA512_Init,&owner));printf("COREUTILS_CRYPTO_COMMONCRYPTO_PROVIDER %s\n",owner.dli_fname);
    for(unsigned i=0;i<3;i++){
        const CryptoHashDescriptor *d=descriptors[i];CHECK(d&&d->init&&d->update&&d->final);
        CHECK(d->digestSize==(i==0?20:i==1?32:64));CHECK(d->blockSize==(i==2?128:64));
        CHECK(CryptoHashDescriptorGetDigestSize(d)==d->digestSize);
    }
    FILE *f=fopen(argv[1],"rb");CHECK(f);
    uint32_t h[7];unsigned counts[3]={0};
    while(fread(h,1,sizeof(h),f)==sizeof(h)){
        cases++;CHECK(h[0]<3&&h[1]<3);const CryptoHashDescriptor *d=descriptors[h[1]];counts[h[0]]++;
        size_t kn=h[2],sn=h[3],in=h[4],dn=h[5],on=h[6];CHECK(on<=64*255);
        unsigned char *key=load(f,kn),*salt=load(f,sn),*info=load(f,in),*data=load(f,dn),*expected=load(f,on);
        unsigned char output[16+64*255+16];memset(output,0xa7,sizeof(output));
        if(h[0]==0){
            CryptoHashOneShot(d,data,dn,output+16);CHECK(!memcmp(output+16,expected,on));
            struct{uint64_t before;CryptoHashContext context;uint64_t after;} guarded={.before=0x123456789abcdef0,.after=0xfedcba9876543210};
            CryptoHashInit(&guarded.context,d);CHECK(guarded.context.descriptor==d);
            for(size_t at=0;at<dn;){size_t take=(at%23)+1;if(take>dn-at)take=dn-at;CryptoHashUpdate(&guarded.context,data+at,take);at+=take;}
            CryptoHashUpdate(&guarded.context,NULL,0);CryptoHashFinal(&guarded.context,output+16);
            CHECK(guarded.before==0x123456789abcdef0&&guarded.after==0xfedcba9876543210);
        }else if(h[0]==1){
            CryptoHMACOneShot(d,key,kn,data,dn,output+16);CHECK(!memcmp(output+16,expected,on));
            struct{uint64_t before;CryptoHMACContext context;uint64_t after;} guarded={.before=0x123456789abcdef0,.after=0xfedcba9876543210};
            CryptoHMACInit(&guarded.context,d,key,kn);CHECK(guarded.context.hash.descriptor==d);
            size_t split=dn/3;CryptoHMACUpdate(&guarded.context,data,split);CryptoHMACUpdate(&guarded.context,data+split,dn-split);CryptoHMACFinal(&guarded.context,output+16);
            CHECK(guarded.before==0x123456789abcdef0&&guarded.after==0xfedcba9876543210);
        }else CryptoHKDF(d,key,kn,salt,sn,info,in,on,output+16);
        CHECK(!memcmp(output+16,expected,on));for(size_t i=0;i<16;i++)CHECK(output[i]==0xa7);
        for(size_t i=16+on;i<sizeof(output);i++)CHECK(output[i]==0xa7);
        free(key);free(salt);free(info);free(data);free(expected);
    }
    CHECK(feof(f)&&!ferror(f));fclose(f);
    printf("COREUTILS_SOURCE_DESCRIPTOR_ABI_HASH_HMAC_HKDF_INDEPENDENT_VECTORS_AND_GUARDS_OK cases=%u hash=%u hmac=%u hkdf=%u checks=%u\n",cases,counts[0],counts[1],counts[2],checks);
}
