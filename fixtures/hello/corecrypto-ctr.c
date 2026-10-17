#include <corecrypto/ccaes.h>
#include <corecrypto/ccmode.h>
#include <dlfcn.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
/* The current Apple private ABI orders setctr before ctr. Legacy Darling
 * orders them the other way; keep the ABI distinction explicit in the test. */
struct native_ctr {
 size_t size,block_size,ecb_block_size;
 int (*init)(const struct ccmode_ctr *,ccctr_ctx *,size_t,const void *,const void *);
 int (*setctr)(const struct ccmode_ctr *,ccctr_ctx *,const void *);
 int (*ctr)(ccctr_ctx *,size_t,const void *,void *);
 const void *custom;
};
static int update(const struct ccmode_ctr *m,ccctr_ctx *ctx,size_t n,const void *in,void *out) {
 if(getenv("CORECRYPTO_VALID_POINTERS_ONLY"))return ((const struct native_ctr *)m)->ctr(ctx,n,in,out);
 return ccctr_update(m,ctx,n,in,out);
}
static int reset(const struct ccmode_ctr *m,ccctr_ctx *ctx,const void *iv) {
 if(getenv("CORECRYPTO_VALID_POINTERS_ONLY"))return ((const struct native_ctr *)m)->setctr(m,ctx,iv);
 return m->setctr(m,ctx,iv);
}
int main(void) {
 setbuf(stdout,NULL);Dl_info owner={0};
 assert(dladdr(ccaes_ctr_crypt_mode,&owner)&&strstr(owner.dli_fname,getenv("CORECRYPTO_EXPECTED_OWNER")?getenv("CORECRYPTO_EXPECTED_OWNER"):"/runtime/corecrypto-hkdf-source/libraries/"));
 const struct ccmode_ctr *mode=ccaes_ctr_crypt_mode();assert(mode->ecb_block_size==16);
 unsigned char key[32],iv[16],plain[1025],out[1025],split[1025],inplace[1025];
 for(size_t i=0;i<32;i++)key[i]=i*7+5;
 for(size_t i=0;i<1025;i++)plain[i]=i*13+11;
 size_t lengths[]={0,1,15,16,17,31,32,33,1025};
 for(size_t kl=16;kl<=32;kl+=8)for(unsigned v=0;v<3;v++)for(unsigned l=0;l<9;l++) {
  size_t n=lengths[l];for(unsigned i=0;i<16;i++)iv[i]=i*11+3;
  if(v==1)memset(iv+8,255,8);if(v==2){memset(iv+8,255,8);iv[15]=254;}
  ccctr_ctx_decl(mode->size,ctx);
  assert(!ccctr_init(mode,ctx,kl,key,iv));assert(!update(mode,ctx,n,plain,out));
  assert(!reset(mode,ctx,iv));
  for(size_t i=0;i<n;i++)assert(!update(mode,ctx,1,plain+i,split+i));
  assert(!memcmp(out,split,n));
  assert(!reset(mode,ctx,iv));memcpy(inplace,plain,n);
  size_t first=n<7?n:7;assert(!update(mode,ctx,first,inplace,inplace));
  assert(!update(mode,ctx,n-first,inplace+first,inplace+first));assert(!memcmp(out,inplace,n));
  assert(!reset(mode,ctx,iv));assert(!update(mode,ctx,n,out,inplace));assert(!memcmp(inplace,plain,n));
  if(!getenv("CORECRYPTO_VALID_POINTERS_ONLY")){assert(!update(mode,ctx,0,NULL,NULL));assert(update(mode,ctx,1,NULL,inplace));}
  printf("CTR %zu %u %zu ",kl,v,n);for(size_t i=0;i<n;i++)printf("%02x",out[i]);puts("");
  ccctr_ctx_clear(mode->size,ctx);
 }
 ccctr_ctx_decl(mode->size,bad);assert(ccctr_init(mode,bad,15,key,iv));
 puts("CORECRYPTO_CTR_BOUNDARIES_OK");return 0;
}
