#import <Foundation/Foundation.h>
#import <QuartzCore/QuartzCore.h>
#import <CoreGraphics/CoreGraphics.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#define CHECK(c) do{if(!(c)){fprintf(stderr,"NATIVE_LAYER_FAIL %d %s\n",__LINE__,#c);return 1;}}while(0)
int main(void){setbuf(stdout,NULL);@autoreleasepool {
 printf("NATIVE_LAYER_MAIN\n");
 uint8_t pixels[16*12*4];memset(pixels,0,sizeof(pixels));
 CGColorSpaceRef space=CGColorSpaceCreateDeviceRGB();CHECK(space);printf("NATIVE_LAYER_COLORSPACE\n");
 CGContextRef context=CGBitmapContextCreate(pixels,16,12,8,16*4,space,kCGImageAlphaPremultipliedLast|kCGBitmapByteOrder32Big);CHECK(context);printf("NATIVE_LAYER_BITMAP_CONTEXT\n");
 CGColorRef red=CGColorCreateGenericRGB(1,0,0,1),blue=CGColorCreateGenericRGB(0,0,1,1);CHECK(red&&blue);
 [CATransaction begin];[CATransaction setDisableActions:YES];
 CALayer *root=[CALayer layer];CHECK(root);root.frame=CGRectMake(0,0,16,12);root.backgroundColor=red;printf("NATIVE_LAYER_CREATED\n");
 CALayer *child=[CALayer layer];CHECK(child);child.frame=CGRectMake(2,3,4,4);child.backgroundColor=blue;[root addSublayer:child];
 [root renderInContext:context];printf("NATIVE_LAYER_RENDER_RETURNED\n");
 [CATransaction commit];
 unsigned reds=0,blues=0,other=0;
 for(unsigned i=0;i<16*12;i++){uint8_t *p=pixels+i*4;if(p[0]>250&&p[1]<5&&p[2]<5&&p[3]>250)reds++;else if(p[0]<5&&p[1]<5&&p[2]>250&&p[3]>250)blues++;else other++;}
 printf("NATIVE_LAYER_PIXELS red=%u blue=%u other=%u\n",reds,blues,other);CHECK(reds==176&&blues==16&&other==0);
 CGColorRelease(red);CGColorRelease(blue);CGContextRelease(context);CGColorSpaceRelease(space);
 printf("NATIVE_LAYER_REAL_BITMAP_TREE_RENDER_OK\n");return 0;
}}
