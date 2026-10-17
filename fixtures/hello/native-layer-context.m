#define DARLING_NATIVE_LAYER_CONTEXT 1
#import <Foundation/Foundation.h>
#import <QuartzCore/CALayerContext.h>
#import <QuartzCore/CALayer.h>
#import <QuartzCore/CATransaction.h>
#import <CoreGraphics/CoreGraphics.h>
#include <objc/runtime.h>
#include <stdio.h>
#include <math.h>
#include <errno.h>
#include <string.h>
static unsigned assertions;
#define CHECK(c) do{assertions++;if(!(c)){fprintf(stderr,"LAYER_CONTEXT_FAIL %d %s\n",__LINE__,#c);exit(1);}}while(0)
static void colors(CGImageRef image,unsigned red,unsigned green,unsigned blue,unsigned clear){
 CHECK(image);CGDataProviderRef provider=CGImageGetDataProvider(image);CFDataRef bytes=CGDataProviderCopyData(provider);CHECK(bytes);
 unsigned r=0,g=0,b=0,t=0,other=0;size_t width=CGImageGetWidth(image),height=CGImageGetHeight(image),row=CGImageGetBytesPerRow(image);const UInt8 *data=CFDataGetBytePtr(bytes);CHECK(CFDataGetLength(bytes)>=row*height);
 for(size_t y=0;y<height;y++)for(size_t x=0;x<width;x++){
  const UInt8 *p=data+y*row+x*4;
  if(p[3]==0)t++;else if(p[0]>250&&p[1]<5&&p[2]<5&&p[3]>250)r++;else if(p[0]<5&&p[1]>250&&p[2]<5&&p[3]>250)g++;else if(p[0]<5&&p[1]<5&&p[2]>250&&p[3]>250)b++;else other++;
 }
 printf("LAYER_CONTEXT_PIXELS red=%u green=%u blue=%u clear=%u other=%u\n",r,g,b,t,other);
 CHECK(r==red&&g==green&&b==blue&&t==clear&&other==0);CFRelease(bytes);
}
@interface CountLayerContext:CALayerContext { @public unsigned count; }
@end
@implementation CountLayerContext
-(void)render {count++;[super render];}
@end
int main(void){setbuf(stdout,NULL);@autoreleasepool{
 CHECK(NSClassFromString(@"CALayerContext")!=NSClassFromString(@"CAContext"));
 printf("LAYER_CONTEXT_MAIN\n");
 CALayerContext *context=[[CALayerContext alloc]initWithFrame:CGRectMake(0,0,16,12)];CHECK(context);
 [CATransaction begin];[CATransaction setDisableActions:YES];
 CALayer *root=[CALayer layer],*child=[CALayer layer];root.frame=CGRectMake(0,0,16,12);child.frame=CGRectMake(2,3,4,4);
 CGColorRef red=CGColorCreateGenericRGB(1,0,0,1),green=CGColorCreateGenericRGB(0,1,0,1),blue=CGColorCreateGenericRGB(0,0,1,1);root.backgroundColor=red;child.backgroundColor=blue;[root addSublayer:child];
 [context setLayer:root];[context render];[context flush];CGImageRef first=[context copyRenderedImage];colors(first,176,0,16,0);
 root.backgroundColor=green;[context render];CGImageRef second=[context copyRenderedImage];colors(second,0,176,16,0);colors(first,176,0,16,0);
 [context setFrame:CGRectMake(1,2,23.25,7.1)];[context setLayer:nil];[context render];CGImageRef empty=[context copyRenderedImage];CHECK(CGImageGetWidth(empty)==24&&CGImageGetHeight(empty)==8);colors(empty,0,0,0,192);
 BOOL caught=NO;@try{[context setFrame:CGRectMake(0,0,NAN,1)];}@catch(NSException *e){caught=[e.name isEqual:NSInvalidArgumentException];}CHECK(caught);
 caught=NO;@try{(void)[context glContext];}@catch(NSException *e){caught=[e.name isEqual:NSInternalInconsistencyException];}CHECK(caught);
 NSObject *window=[NSObject new];caught=NO;@try{[context setSubwindow:(id)window];}@catch(NSException *e){caught=[e.name isEqual:NSInvalidArgumentException];}CHECK(caught);[window release];
 [context setSubwindow:nil];caught=NO;@try{[context deleteTextureId:@1];}@catch(NSException *e){caught=[e.name isEqual:NSInvalidArgumentException];}CHECK(caught);
 [context invalidate];[context invalidate];caught=NO;@try{[context render];}@catch(NSException *e){caught=[e.name isEqual:NSInternalInconsistencyException];}CHECK(caught);[context release];
 CGImageRelease(first);CGImageRelease(second);CGImageRelease(empty);
 context=[[CALayerContext alloc]initWithFrame:CGRectZero];[context render];errno=0;CHECK([context copyRenderedImage]==NULL&&errno==ENOENT);[context setFrame:CGRectMake(0,0,2,2)];[context render];CGImageRef resized=[context copyRenderedImage];colors(resized,0,0,0,4);CGImageRelease(resized);[context invalidate];[context release];
 CountLayerContext *timed=[[CountLayerContext alloc]initWithFrame:CGRectMake(0,0,2,2)];[timed startTimerIfNeeded];[timed startTimerIfNeeded];[[NSRunLoop currentRunLoop]runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.08]];CHECK(timed->count>0);[timed invalidate];unsigned before=timed->count;[[NSRunLoop currentRunLoop]runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.04]];CHECK(timed->count==before);[timed release];
 [CATransaction commit];CGColorRelease(red);CGColorRelease(green);CGColorRelease(blue);
 printf("SOURCE_CALAYER_CONTEXT_BITMAP_TREE_SNAPSHOT_RESIZE_CLEAR_ERRORS_AND_TIMER_OK %u\n",assertions);return 0;
}}
