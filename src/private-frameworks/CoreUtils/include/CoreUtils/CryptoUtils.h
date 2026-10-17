/* CoreUtils' x86_64 digest descriptor/context ABI, backed by CommonCrypto. */
#ifndef DARLING_COREUTILS_CRYPTOUTILS_H
#define DARLING_COREUTILS_CRYPTOUTILS_H
#include <stddef.h>
#include <stdint.h>
#include <CommonCrypto/CommonDigest.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct CryptoHashContext CryptoHashContext;
typedef struct CryptoHashDescriptor {
    void (*init)(CryptoHashContext *);
    void (*update)(CryptoHashContext *,const void *,size_t);
    void (*final)(CryptoHashContext *,void *);
    size_t digestSize;
    size_t blockSize;
} CryptoHashDescriptor;
struct CryptoHashContext {
    const CryptoHashDescriptor *descriptor;
    union { CC_SHA1_CTX sha1; CC_SHA256_CTX sha256; CC_SHA512_CTX sha512; } state;
};
typedef struct CryptoHMACContext {
    CryptoHashContext hash;
    uint8_t outerPad[128];
} CryptoHMACContext;
extern const CryptoHashDescriptor * const kCryptoHashDescriptor_SHA1;
extern const CryptoHashDescriptor * const kCryptoHashDescriptor_SHA256;
extern const CryptoHashDescriptor * const kCryptoHashDescriptor_SHA512;
size_t CryptoHashDescriptorGetDigestSize(const CryptoHashDescriptor *descriptor);
void CryptoHashInit(CryptoHashContext *ctx,const CryptoHashDescriptor *descriptor);
void CryptoHashUpdate(CryptoHashContext *ctx,const void *data,size_t length);
void CryptoHashFinal(CryptoHashContext *ctx,void *digest);
void CryptoHashOneShot(const CryptoHashDescriptor *descriptor,const void *data,size_t length,void *digest);
void CryptoHMACInit(CryptoHMACContext *ctx,const CryptoHashDescriptor *descriptor,const void *key,size_t length);
void CryptoHMACUpdate(CryptoHMACContext *ctx,const void *data,size_t length);
void CryptoHMACFinal(CryptoHMACContext *ctx,void *digest);
void CryptoHMACOneShot(const CryptoHashDescriptor *descriptor,const void *key,size_t keyLength,const void *data,size_t dataLength,void *digest);
void CryptoHKDF(const CryptoHashDescriptor *descriptor,const void *key,size_t keyLength,const void *salt,size_t saltLength,const void *info,size_t infoLength,size_t outputLength,void *output);
#ifdef __cplusplus
}
#endif
#endif
