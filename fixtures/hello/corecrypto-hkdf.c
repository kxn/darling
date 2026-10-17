#include <corecrypto/cchkdf.h>
#include <corecrypto/cchmac.h>
#include <corecrypto/ccsha1.h>
#include <corecrypto/ccsha2.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
static void hex(const unsigned char *b,size_t n) { for(size_t i=0;i<n;i++) printf("%02x",b[i]); puts(""); }
int main(void) {
 setbuf(stdout,NULL);Dl_info owner={0};
 assert(dladdr(cchkdf,&owner)&&strstr(owner.dli_fname,getenv("CORECRYPTO_EXPECTED_OWNER")?getenv("CORECRYPTO_EXPECTED_OWNER"):"/runtime/corecrypto-hkdf-source/libraries/"));
 printf("CORECRYPTO_HKDF_OWNER %s\n",owner.dli_fname);
 const struct ccdigest_info *digests[]={ccsha1_di(),ccsha224_di(),ccsha256_di(),ccsha384_di(),ccsha512_di()};
 const char *names[]={"sha1","sha224","sha256","sha384","sha512"};
 unsigned char key[1024],salt[1024],info[1024],message[1024],out[16321],prk[64],two[16321];
 for(size_t i=0;i<1024;i++){key[i]=(i*17+3)&255;salt[i]=(i*23+7)&255;info[i]=(i*31+11)&255;message[i]=(i*47+13)&255;}
 for(unsigned d=0;d<5;d++) {
  const struct ccdigest_info *di=digests[d];size_t sizes[]={0,1,di->block_size-1,di->block_size,di->block_size+1,1024};
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
 puts("CORECRYPTO_HKDF_BOUNDARIES_OK");return 0;
}
