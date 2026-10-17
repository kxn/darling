#include <corecrypto/ccec25519.h>
#include <corecrypto/ccsha2.h>
#include <assert.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
struct rng { struct ccrng_state state; unsigned value; int fail; };
static int generate(struct ccrng_state *state,size_t n,void *out) {
 struct rng *rng=(void *)state;if(rng->fail)return -777;
 for(size_t i=0;i<n;i++)((unsigned char *)out)[i]=(rng->value++ * 17+3)&255;
 return 0;
}
static void hex(const void *buf,size_t n) {const unsigned char *b=buf;for(size_t i=0;i<n;i++)printf("%02x",b[i]);}
int main(void) {
 setbuf(stdout,NULL);Dl_info owner={0};assert(dladdr(cccurve25519_make_priv,&owner)&&strstr(owner.dli_fname,getenv("CORECRYPTO_EXPECTED_OWNER")?getenv("CORECRYPTO_EXPECTED_OWNER"):"/runtime/corecrypto-hkdf-source/libraries/"));
 struct rng rng={{generate},0,0};unsigned char sk[32],pk[32],peer[32],peerpk[32],out[32],other[32];
 assert(!cccurve25519_make_key_pair(&rng.state,pk,sk));
 for(unsigned i=0;i<32;i++)assert(sk[i]==(i==0?(((i*17+3)&255)&248):(i==31?(((i*17+3)&127)|64):((i*17+3)&255))));
 rng.fail=1;memset(sk,0xA5,32);assert(cccurve25519_make_key_pair(&rng.state,pk,sk)==-777);
 if(!getenv("CORECRYPTO_VALID_POINTERS_ONLY"))for(unsigned i=0;i<32;i++)assert(!sk[i]&&!pk[i]);
 rng.fail=0;
 for(unsigned k=0;k<16;k++) {
  for(unsigned i=0;i<32;i++){sk[i]=k*13+i*7+11;peer[i]=k*19+i*11+5;}
  assert(!cccurve25519_make_pub_with_rng(&rng.state,pk,sk));assert(!cccurve25519_make_pub(peerpk,peer));
  assert(!cccurve25519_with_rng(&rng.state,out,sk,peerpk));assert(!cccurve25519(other,peer,pk));assert(!memcmp(out,other,32));
  printf("X25519 %u ",k);hex(pk,32);putchar(' ');hex(peerpk,32);putchar(' ');hex(out,32);putchar('\n');
  memset(peerpk,0,32);assert(cccurve25519(out,sk,peerpk));if(!getenv("CORECRYPTO_VALID_POINTERS_ONLY"))for(unsigned i=0;i<32;i++)assert(!out[i]);
 }
 unsigned char signature[64],changed[64],message[129];for(unsigned i=0;i<129;i++)message[i]=i*23+7;
 const size_t lengths[]={0,1,31,32,64,129};
 for(unsigned k=0;k<16;k++) {
  for(unsigned i=0;i<32;i++)sk[i]=k*29+i*17+9;
  assert(!cced25519_make_pub(ccsha512_di(),pk,sk));
  for(unsigned j=0;j<6;j++) {
   size_t n=lengths[j];assert(!cced25519_sign(ccsha512_di(),signature,n,message,pk,sk));assert(!cced25519_verify(ccsha512_di(),n,message,signature,pk));
   memcpy(changed,signature,64);changed[0]^=1;assert(cced25519_verify(ccsha512_di(),n,message,changed,pk));
   message[0]^=1;assert(cced25519_verify(ccsha512_di(),n?n:1,message,signature,pk));message[0]^=1;
   printf("ED25519 %u %zu ",k,n);hex(pk,32);putchar(' ');hex(signature,64);putchar('\n');
  }
  if(!getenv("CORECRYPTO_VALID_POINTERS_ONLY")) {
   pk[0]^=1;assert(cced25519_sign(ccsha512_di(),signature,1,message,pk,sk));
   assert(cced25519_make_pub(ccsha256_di(),pk,sk));
  }
 }
 rng.value=0;assert(!cced25519_make_key_pair(ccsha512_di(),&rng.state,pk,sk));
 for(unsigned i=0;i<32;i++)assert(sk[i]==((i*17+3)&255));
 printf("ED25519_GENERATED ");hex(pk,32);putchar('\n');
 rng.fail=1;assert(cced25519_make_key_pair(ccsha512_di(),&rng.state,pk,sk)==-777);if(!getenv("CORECRYPTO_VALID_POINTERS_ONLY"))for(unsigned i=0;i<32;i++)assert(!sk[i]&&!pk[i]);
 puts("CORECRYPTO_25519_KEYS_SIGNATURE_TAMPER_ZERO_PEER_RNG_ERRORS_OK");return 0;
}
