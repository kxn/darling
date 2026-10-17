#include <corecrypto/cchkdf.h>
#include <corecrypto/cchmac.h>
#include <corecrypto/ccsha3.h>
#include <stdlib.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
static void hex(const unsigned char *b,size_t n) { for(size_t i=0;i<n;i++) printf("%02x",b[i]); puts(""); }
int main(void) {
 setbuf(stdout,NULL);Dl_info owner={0};
 assert(dladdr(ccsha3_256_di,&owner)&&strstr(owner.dli_fname,getenv("CORECRYPTO_EXPECTED_OWNER")?getenv("CORECRYPTO_EXPECTED_OWNER"):"/runtime/corecrypto-hkdf-source/libraries/"));
 printf("CORECRYPTO_HKDF_OWNER %s\n",owner.dli_fname);
 const struct ccdigest_info *digests[]={ccsha3_224_di(),ccsha3_256_di(),ccsha3_384_di(),ccsha3_512_di()};
 const char *names[]={"sha3_224","sha3_256","sha3_384","sha3_512"};
 unsigned char key[1024],salt[1024],info[1024],message[1024],out[16321],prk[64],two[16321];
 for(size_t i=0;i<1024;i++){key[i]=(i*17+3)&255;salt[i]=(i*23+7)&255;info[i]=(i*31+11)&255;message[i]=(i*47+13)&255;}
 for(unsigned d=0;d<4;d++) {
  const struct ccdigest_info *di=digests[d];
  size_t lengths[]={0,1,7,8,9,63,64,65,di->block_size-1,di->block_size,di->block_size+1,2*di->block_size-1,2*di->block_size,2*di->block_size+1,4095,4096,1000003};
  unsigned char *large=malloc(1000004);assert(large);
  for(size_t i=0;i<1000004;i++)large[i]=(i*29+(i>>8)+19)&255;
  for(unsigned l=0;l<17;l++) {
   unsigned char digest[64],incremental[64],bytewise[64];size_t n=lengths[l];
   ccdigest(di,n,large+1,digest);ccdigest_di_decl(di,ctx);ccdigest_init(di,ctx);
   for(size_t i=0;i<n;){size_t step=1+(i%137);if(step>n-i)step=n-i;ccdigest_update(di,ctx,step,large+1+i);i+=step;}
   ccdigest_final(di,ctx,incremental);assert(!memcmp(digest,incremental,di->output_size));
   if(n<8192){ccdigest_init(di,ctx);for(size_t i=0;i<n;i++)ccdigest_update(di,ctx,1,large+1+i);ccdigest_final(di,ctx,bytewise);assert(!memcmp(digest,bytewise,di->output_size));}
   ccdigest_di_clear(di,ctx);printf("DIGEST %s %zu ",names[d],n);hex(digest,di->output_size);
  }
  free(large);
  size_t sizes[]={0,1,di->block_size-1,di->block_size,di->block_size+1,1024};
  for(unsigned i=0;i<6;i++)for(unsigned j=0;j<6;j++) {
   cchmac(di,sizes[i],key,sizes[j],message,out);
   printf("HMAC %s %zu %zu ",names[d],sizes[i],sizes[j]);hex(out,di->output_size);
  }
  size_t outputs[]={0,1,di->output_size-1,di->output_size,di->output_size+1,255*di->output_size};
  for(unsigned i=0;i<6;i++) {
   size_t il=sizes[i],sl=sizes[5-i],cl=sizes[(i+2)%6],ol=outputs[i];
   assert(!cchkdf(di,il,key,sl,salt,cl,info,ol,out));
   assert(!cchkdf_extract(di,sl,salt,il,key,prk));
   assert(!cchkdf_expand(di,di->output_size,prk,cl,info,ol,two));assert(!memcmp(out,two,ol));
   printf("HKDF %s %zu %zu %zu %zu ",names[d],il,sl,cl,ol);hex(out,ol);
  }
  memset(out,0xA5,sizeof(out));assert(cchkdf(di,1,key,1,salt,1,info,255*di->output_size+1,out));
  for(size_t i=0;i<sizeof(out);i++)assert(out[i]==0xA5);
  if(!getenv("CORECRYPTO_VALID_POINTERS_ONLY")) {
  assert(cchkdf(di,1,NULL,0,NULL,0,NULL,1,out));
  assert(cchkdf_expand(di,1,key,1,NULL,1,out));
  assert(cchkdf_extract(di,1,NULL,0,NULL,prk));
  assert(!cchkdf(di,0,NULL,0,NULL,0,NULL,0,NULL));
  }
 }
 if(!getenv("CORECRYPTO_VALID_POINTERS_ONLY")) assert(cchkdf(NULL,0,NULL,0,NULL,0,NULL,0,NULL));
 puts("CORECRYPTO_SHA3_HASH_HMAC_HKDF_BOUNDARIES_OK");return 0;
}
