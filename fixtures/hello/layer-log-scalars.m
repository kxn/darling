#import <Foundation/Foundation.h>
#import <CoreGraphics/CoreGraphics.h>
#include <os/log.h>
#include <dlfcn.h>
#include <fenv.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
extern bool CGFloatIsValid(CGFloat);
extern bool reference_CGFloatIsValid(CGFloat);
extern int os_log_compare_enablement(os_log_type_t,os_log_type_t);
extern int reference_os_log_compare_enablement(os_log_type_t,os_log_type_t);
extern CGAffineTransform CGContextGetBaseCTM(CGContextRef);
extern void CGContextSetBaseCTM(CGContextRef,CGAffineTransform);
static unsigned checks,values;
#define CHECK(c) do{checks++;if(!(c)){fprintf(stderr,"LAYER_LOG_FAIL line=%d %s\n",__LINE__,#c);exit(1);}}while(0)
static void scalar(uint64_t bits){
 double value;memcpy(&value,&bits,8);
 feclearexcept(FE_ALL_EXCEPT);bool expected=reference_CGFloatIsValid(value);int ef=fetestexcept(FE_ALL_EXCEPT);
 feclearexcept(FE_ALL_EXCEPT);bool actual=CGFloatIsValid(value);int af=fetestexcept(FE_ALL_EXCEPT);
 CHECK(expected==actual&&af==ef&&af==0);values++;
}
static void matrix(CGAffineTransform a,CGAffineTransform b){CHECK(a.a==b.a&&a.b==b.b&&a.c==b.c&&a.d==b.d&&a.tx==b.tx&&a.ty==b.ty);}
int main(int argc,char **argv){setbuf(stdout,NULL);@autoreleasepool{
 if(argc>1){volatile int result=os_log_compare_enablement((os_log_type_t)strtoul(argv[1],NULL,0),OS_LOG_TYPE_DEFAULT);printf("UNEXPECTED_INVALID_ENUM_RETURN %d\n",result);return 2;}
 uint64_t explicit[]={0,UINT64_C(0x8000000000000000),1,UINT64_C(0x8000000000000001),UINT64_C(0x000fffffffffffff),UINT64_C(0x0010000000000000),UINT64_C(0x7fefffffffffffff),UINT64_C(0xffefffffffffffff),UINT64_C(0x7ff0000000000000),UINT64_C(0xfff0000000000000),UINT64_C(0x7ff0000000000001),UINT64_C(0xfff0000000000001),UINT64_C(0x7ff8000000000000),UINT64_C(0xffffffffffffffff)};
 for(unsigned i=0;i<sizeof(explicit)/sizeof(*explicit);i++)scalar(explicit[i]);
 for(uint64_t e=0;e<2048;e++)for(uint64_t sign=0;sign<2;sign++){scalar((sign<<63)|(e<<52));scalar((sign<<63)|(e<<52)|UINT64_C(0xfffffffffffff));}
 uint64_t state=UINT64_C(0xa461be229a3f1761);for(unsigned i=0;i<10000;i++){state^=state<<13;state^=state>>7;state^=state<<17;scalar(state);}
 printf("CGFLOAT_NATIVE_DIFFERENTIAL_AND_FP_FLAGS_OK values=%u\n",values);
 os_log_type_t types[]={OS_LOG_TYPE_DEBUG,OS_LOG_TYPE_INFO,OS_LOG_TYPE_DEFAULT,OS_LOG_TYPE_ERROR,OS_LOG_TYPE_FAULT};
 for(unsigned i=0;i<5;i++)for(unsigned j=0;j<5;j++){int v=os_log_compare_enablement(types[i],types[j]);CHECK(v==reference_os_log_compare_enablement(types[i],types[j]));CHECK(v==(int)i-(int)j);}
 Dl_info owner;CHECK(dladdr((void *)os_log_compare_enablement,&owner)&&strstr(owner.dli_fname,"/runtime/libtrace-enablement-source/"));
 puts("LOG_COMPARE_ALL_25_ORIGINAL_INSTRUCTION_RESULTS_AND_SOURCE_OWNER_OK");
 unsigned char pixels[8*8*4]={0};CGColorSpaceRef rgb=CGColorSpaceCreateDeviceRGB();CGContextRef c=CGBitmapContextCreate(pixels,8,8,8,32,rgb,kCGImageAlphaPremultipliedLast|kCGBitmapByteOrder32Big);CHECK(c);CGColorSpaceRelease(rgb);
 CGAffineTransform initial=CGContextGetBaseCTM(c),physical=CGContextGetUserSpaceToDeviceSpaceTransform(c);matrix(initial,physical);
 CGAffineTransform user=CGAffineTransformMake(2,0,0,3,1,2),base=CGAffineTransformMake(4,1,2,5,6,7),replacement=CGAffineTransformMake(8,2,1,9,11,13);
 CGContextConcatCTM(c,user);CGAffineTransform saved=CGContextGetCTM(c),device=CGContextGetUserSpaceToDeviceSpaceTransform(c);matrix(initial,CGContextGetBaseCTM(c));
 CGContextSetBaseCTM(c,base);matrix(base,CGContextGetBaseCTM(c));matrix(saved,CGContextGetCTM(c));matrix(device,CGContextGetUserSpaceToDeviceSpaceTransform(c));
 CGContextSaveGState(c);CGContextTranslateCTM(c,3,4);CGContextSetBaseCTM(c,replacement);CGContextRestoreGState(c);
 matrix(saved,CGContextGetCTM(c));matrix(device,CGContextGetUserSpaceToDeviceSpaceTransform(c));matrix(replacement,CGContextGetBaseCTM(c));
 CGContextSetBaseCTM(c,initial);CGContextRelease(c);
 // Render through the same nonidentity public CTM after changing private base
 // metadata. Physical geometry must not receive the base transform twice.
 memset(pixels,0,sizeof(pixels));rgb=CGColorSpaceCreateDeviceRGB();c=CGBitmapContextCreate(pixels,8,8,8,32,rgb,kCGImageAlphaPremultipliedLast|kCGBitmapByteOrder32Big);CGColorSpaceRelease(rgb);CHECK(c);
 CGContextSetBaseCTM(c,base);CGContextTranslateCTM(c,2,3);CGContextScaleCTM(c,2,2);CGContextSetRGBFillColor(c,1,0,0,1);CGContextFillRect(c,CGRectMake(0,0,2,1));
 unsigned red=0,clear=0;for(unsigned i=0;i<64;i++){unsigned char *p=pixels+4*i;if(p[0]==255&&p[1]==0&&p[2]==0&&p[3]==255)red++;else if(!p[0]&&!p[1]&&!p[2]&&!p[3])clear++;}
 CHECK(red==8&&clear==56);CGContextRelease(c);
 printf("BASE_CTM_INDEPENDENT_RENDER_STATE_GSTATE_AND_TRANSFORMED_PIXELS_OK checks=%u\n",checks);return 0;
}}
