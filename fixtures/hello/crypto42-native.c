#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include <openssl/aes.h>
#include <openssl/camellia.h>
#include "native-addresses.h"
static unsigned checks,counts[7];
#define CHECK(x) do { checks++; if(!(x)){fprintf(stderr,"FAIL line=%d %s\n",__LINE__,#x);exit(1);} } while(0)
static void *library,*base;
static void *symbol(const char *name){void *p=dlsym(library,name);Dl_info info={0};CHECK(p&&dladdr(p,&info)&&strstr(info.dli_fname,"cryptex-native/libraries/libcrypto.42.dylib"));return p;}
static void *internal(uintptr_t offset){return (char*)base+offset;}
static void load(FILE *f,void *p,size_t n){CHECK(fread(p,1,n,f)==n);}
typedef int(*aes_set)(const unsigned char*,int,AES_KEY*);
typedef void(*aes_block)(const unsigned char*,unsigned char*,const AES_KEY*);
typedef void(*aes_cbc)(const unsigned char*,unsigned char*,size_t,const AES_KEY*,unsigned char*,int);
static void guards(const unsigned char *p,size_t n,unsigned char value){for(size_t i=0;i<n;i++)CHECK(p[i]==value);}
static void aes_check(const unsigned char *key,unsigned bits,const unsigned char *iv,const unsigned char *data,size_t n,const unsigned char *expected){
    struct __attribute__((aligned(16))){unsigned char prefix[32];AES_KEY key;unsigned char suffix[32];} enc,dec;
    unsigned char output[4128],plain[4128],current_iv[16];
    aes_set setenc=symbol("AES_set_encrypt_key"),setdec=symbol("AES_set_decrypt_key");aes_block encrypt=symbol("AES_encrypt"),decrypt=symbol("AES_decrypt");aes_cbc cbc=symbol("AES_cbc_encrypt");
    memset(&enc,0xa5,sizeof(enc));memset(&dec,0xa5,sizeof(dec));CHECK(setenc(key,bits,&enc.key)==0&&setdec(key,bits,&dec.key)==0);
    guards(enc.prefix,32,0xa5);guards(enc.suffix,32,0xa5);guards(dec.prefix,32,0xa5);guards(dec.suffix,32,0xa5);
    memset(output,0xa5,sizeof(output));encrypt(data,output+16,&enc.key);CHECK(!memcmp(output+16,expected+n,16));decrypt(output+16,plain,&dec.key);CHECK(!memcmp(plain,data,16));
    memcpy(current_iv,iv,16);cbc(data,output+16,n,&enc.key,current_iv,1);CHECK(!memcmp(output+16,expected,n));guards(output,16,0xa5);guards(output+16+n,sizeof(output)-16-n,0xa5);
    memcpy(current_iv,iv,16);cbc(output+16,plain,n,&dec.key,current_iv,0);CHECK(!memcmp(plain,data,n));
    aes_set vsetenc=internal(OFFSET_vpaes_set_encrypt_key),vsetdec=internal(OFFSET_vpaes_set_decrypt_key);aes_block vencrypt=internal(OFFSET_vpaes_encrypt),vdecrypt=internal(OFFSET_vpaes_decrypt);aes_cbc vcbc=internal(OFFSET_vpaes_cbc_encrypt),bcbc=internal(OFFSET_bsaes_cbc_encrypt);
    CHECK(vsetenc(key,bits,&enc.key)==0&&vsetdec(key,bits,&dec.key)==0);vencrypt(data,output+16,&enc.key);CHECK(!memcmp(output+16,expected+n,16));vdecrypt(output+16,plain,&dec.key);CHECK(!memcmp(plain,data,16));
    memcpy(current_iv,iv,16);vcbc(data,output+16,n,&enc.key,current_iv,1);CHECK(!memcmp(output+16,expected,n));memcpy(current_iv,iv,16);vcbc(output+16,plain,n,&dec.key,current_iv,0);CHECK(!memcmp(plain,data,n));
    CHECK(setenc(key,bits,&enc.key)==0&&setdec(key,bits,&dec.key)==0);memcpy(current_iv,iv,16);bcbc(data,output+16,n,&enc.key,current_iv,1);CHECK(!memcmp(output+16,expected,n));memcpy(current_iv,iv,16);bcbc(output+16,plain,n,&dec.key,current_iv,0);CHECK(!memcmp(plain,data,n));
    guards(enc.prefix,32,0xa5);guards(enc.suffix,32,0xa5);guards(dec.prefix,32,0xa5);guards(dec.suffix,32,0xa5);
}
static void camellia_check(const unsigned char *key,unsigned bits,const unsigned char *iv,const unsigned char *data,size_t n,const unsigned char *expected){
    struct __attribute__((aligned(16))){unsigned char prefix[32];CAMELLIA_KEY key;unsigned char suffix[32];} ctx;
    int(*set)(const unsigned char*,int,CAMELLIA_KEY*)=symbol("Camellia_set_key");void(*enc)(const unsigned char*,unsigned char*,const CAMELLIA_KEY*)=symbol("Camellia_encrypt"),(*dec)(const unsigned char*,unsigned char*,const CAMELLIA_KEY*)=symbol("Camellia_decrypt");void(*cbc)(const unsigned char*,unsigned char*,size_t,const CAMELLIA_KEY*,unsigned char*,int)=symbol("Camellia_cbc_encrypt");
    unsigned char out[4128],plain[4096],current_iv[16];memset(&ctx,0xa5,sizeof(ctx));CHECK(set(key,bits,&ctx.key)==0);memset(out,0xa5,sizeof(out));enc(data,out+16,&ctx.key);CHECK(!memcmp(out+16,expected+n,16));dec(out+16,plain,&ctx.key);CHECK(!memcmp(plain,data,16));memcpy(current_iv,iv,16);cbc(data,out+16,n,&ctx.key,current_iv,1);CHECK(!memcmp(out+16,expected,n));memcpy(current_iv,iv,16);cbc(out+16,plain,n,&ctx.key,current_iv,0);CHECK(!memcmp(plain,data,n));guards(out,16,0xa5);guards(out+16+n,sizeof(out)-16-n,0xa5);guards(ctx.prefix,32,0xa5);guards(ctx.suffix,32,0xa5);
}
static uint64_t big64(const unsigned char *p){uint64_t value=0;for(unsigned i=0;i<8;i++)value=(value<<8)|p[i];return value;}
static void ghash_check(const unsigned char *key,const unsigned char *iv,const unsigned char *data,size_t n,const unsigned char *expected){
    unsigned char tables[512] __attribute__((aligned(16))),xi[16];
    void(*mult4)(void*,const void*)=internal(OFFSET_gcm_gmult_4bit),(*multc)(void*,const void*)=internal(OFFSET_gcm_gmult_clmul);void(*hash4)(void*,const void*,const void*,size_t)=internal(OFFSET_gcm_ghash_4bit),(*hashc)(void*,const void*,const void*,size_t)=internal(OFFSET_gcm_ghash_clmul),(*initc)(void*,const void*)=internal(OFFSET_gcm_init_clmul);
    memcpy(tables,key+16,256);memcpy(xi,iv,16);mult4(xi,tables);CHECK(!memcmp(xi,expected,16));memcpy(xi,iv,16);hash4(xi,tables,data,n);CHECK(!memcmp(xi,expected+16,16));
    uint64_t h[2]={big64(key),big64(key+8)};memset(tables,0xa5,sizeof(tables));initc(tables,h);memcpy(xi,iv,16);multc(xi,tables);CHECK(!memcmp(xi,expected,16));memcpy(xi,iv,16);hashc(xi,tables,data,n);CHECK(!memcmp(xi,expected+16,16));
}
int main(int argc,char **argv){
    setbuf(stdout,NULL);CHECK(argc==2);library=dlopen("/usr/lib/libcrypto.42.dylib",RTLD_LAZY|RTLD_LOCAL);if(!library){fprintf(stderr,"%s\n",dlerror());return 2;}Dl_info info;CHECK(dladdr(symbol("AES_encrypt"),&info));base=info.dli_fbase;printf("NATIVE_CRYPTO42_PROVIDER %s AES_KEY=%zu CAMELLIA_KEY=%zu\n",info.dli_fname,sizeof(AES_KEY),sizeof(CAMELLIA_KEY));
    FILE *f=fopen(argv[1],"rb");CHECK(f);uint32_t total;load(f,&total,4);
    for(unsigned i=0;i<total;i++){
        uint32_t fields[4];load(f,fields,sizeof(fields));unsigned kind=fields[0],kn=fields[1],n=fields[2],on=fields[3];CHECK(kind<7&&kn<=512&&n<=4096&&on<=4112);unsigned char key[512],iv[16],data[4096],expected[4112];load(f,key,kn);load(f,iv,16);load(f,data,n);load(f,expected,on);
        if(kind<4){const char *names[]={"SHA1","SHA256","SHA512","WHIRLPOOL"};unsigned char output[96];memset(output,0xa5,sizeof(output));unsigned char*(*hash)(const void*,size_t,unsigned char*)=symbol(names[kind]);CHECK(hash(data,n,output+16)==output+16);CHECK(!memcmp(output+16,expected,on));guards(output,16,0xa5);guards(output+16+on,sizeof(output)-16-on,0xa5);}
        else if(kind==4)aes_check(key,kn*8,iv,data,n,expected);
        else if(kind==5)camellia_check(key,kn*8,iv,data,n,expected);
        else ghash_check(key,iv,data,n,expected);
        counts[kind]++;
    }
    CHECK(fgetc(f)==EOF);CHECK(fclose(f)==0);printf("NATIVE_CRYPTO42_INDEPENDENT_DIGEST_AES_VPAES_BSAES_CAMELLIA_GHASH_4BIT_CLMUL_AND_GUARDS_OK cases=%u checks=%u counts=",total,checks);for(unsigned i=0;i<7;i++)printf("%u%s",counts[i],i==6?"\n":",");return 0;
}
