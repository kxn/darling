#include <CoreUtils/CryptoUtils.h>
#include <string.h>
#include <errno.h>

static void wipe(void *data,size_t length){volatile uint8_t *p=data;while(length--)*p++=0;}

#if defined(__x86_64__)
_Static_assert(sizeof(CryptoHashDescriptor)==40,"native digest descriptor ABI");
_Static_assert(offsetof(CryptoHashContext,state)==8,"native digest state offset");
_Static_assert(sizeof(CryptoHashContext)==216,"native digest context ABI");
_Static_assert(offsetof(CryptoHMACContext,outerPad)==216,"native HMAC pad offset");
_Static_assert(sizeof(CryptoHMACContext)==344,"native HMAC context ABI");
#endif

#define DIGEST_IMPL(name,member) \
static void name##Init(CryptoHashContext *c){CC_##name##_Init(&c->state.member);} \
static void name##Update(CryptoHashContext *c,const void *p,size_t n){CC_##name##_Update(&c->state.member,p,(CC_LONG)n);} \
static void name##Final(CryptoHashContext *c,void *p){CC_##name##_Final(p,&c->state.member);}
DIGEST_IMPL(SHA1,sha1)
DIGEST_IMPL(SHA256,sha256)
DIGEST_IMPL(SHA512,sha512)
static const CryptoHashDescriptor sha1={SHA1Init,SHA1Update,SHA1Final,20,64};
static const CryptoHashDescriptor sha256={SHA256Init,SHA256Update,SHA256Final,32,64};
static const CryptoHashDescriptor sha512={SHA512Init,SHA512Update,SHA512Final,64,128};
const CryptoHashDescriptor * const kCryptoHashDescriptor_SHA1=&sha1;
const CryptoHashDescriptor * const kCryptoHashDescriptor_SHA256=&sha256;
const CryptoHashDescriptor * const kCryptoHashDescriptor_SHA512=&sha512;

size_t CryptoHashDescriptorGetDigestSize(const CryptoHashDescriptor *d){return d->digestSize;}
void CryptoHashInit(CryptoHashContext *c,const CryptoHashDescriptor *d){c->descriptor=d;d->init(c);}
void CryptoHashUpdate(CryptoHashContext *c,const void *p,size_t n){c->descriptor->update(c,p,n);}
void CryptoHashFinal(CryptoHashContext *c,void *p){c->descriptor->final(c,p);}
void CryptoHashOneShot(const CryptoHashDescriptor *d,const void *p,size_t n,void *out){
    CryptoHashContext c;CryptoHashInit(&c,d);CryptoHashUpdate(&c,p,n);CryptoHashFinal(&c,out);
}
void CryptoHMACInit(CryptoHMACContext *c,const CryptoHashDescriptor *d,const void *key,size_t n){
    uint8_t shortened[64],inner[128];const uint8_t *bytes=key;
    if(n>d->blockSize){CryptoHashOneShot(d,key,n,shortened);bytes=shortened;n=d->digestSize;}
    for(size_t i=0;i<d->blockSize;i++){
        uint8_t byte=i<n?bytes[i]:0;inner[i]=byte^0x36;c->outerPad[i]=byte^0x5c;
    }
    CryptoHashInit(&c->hash,d);CryptoHashUpdate(&c->hash,inner,d->blockSize);
    wipe(shortened,sizeof(shortened));wipe(inner,sizeof(inner));
}
void CryptoHMACUpdate(CryptoHMACContext *c,const void *p,size_t n){CryptoHashUpdate(&c->hash,p,n);}
void CryptoHMACFinal(CryptoHMACContext *c,void *out){
    const CryptoHashDescriptor *d=c->hash.descriptor;
    CryptoHashFinal(&c->hash,out);CryptoHashInit(&c->hash,d);
    CryptoHashUpdate(&c->hash,c->outerPad,d->blockSize);CryptoHashUpdate(&c->hash,out,d->digestSize);CryptoHashFinal(&c->hash,out);
}
void CryptoHMACOneShot(const CryptoHashDescriptor *d,const void *key,size_t kn,const void *p,size_t n,void *out){
    CryptoHMACContext c;CryptoHMACInit(&c,d,key,kn);CryptoHMACUpdate(&c,p,n);CryptoHMACFinal(&c,out);wipe(&c,sizeof(c));
}
void CryptoHKDF(const CryptoHashDescriptor *d,const void *key,size_t kn,const void *salt,size_t sn,const void *info,size_t in,size_t n,void *out){
    if(n>d->digestSize*255){errno=EINVAL;return;}
    uint8_t zero[64]={0},prk[64],previous[64];size_t previousSize=0;uint8_t *destination=out;
    if(sn==0){salt=zero;sn=d->digestSize;}
    CryptoHMACOneShot(d,salt,sn,key,kn,prk);
    for(unsigned counter=1;n;counter++){
        CryptoHMACContext c;uint8_t byte=counter;
        CryptoHMACInit(&c,d,prk,d->digestSize);CryptoHMACUpdate(&c,previous,previousSize);
        CryptoHMACUpdate(&c,info,in);CryptoHMACUpdate(&c,&byte,1);CryptoHMACFinal(&c,previous);
        size_t take=n<d->digestSize?n:d->digestSize;memcpy(destination,previous,take);destination+=take;n-=take;previousSize=d->digestSize;
        wipe(&c,sizeof(c));
    }
    wipe(prk,sizeof(prk));wipe(previous,sizeof(previous));
}
