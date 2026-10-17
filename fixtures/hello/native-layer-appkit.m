#define DARLING_NATIVE_LAYER_CONTEXT 1
#import <AppKit/AppKit.h>
#import <QuartzCore/CALayer.h>
#import <QuartzCore/CATransaction.h>
#import <QuartzCore/CALayerContext.h>
#include <objc/runtime.h>
#include <stdio.h>
#include <stdlib.h>
#define CHECK(c) do{if(!(c)){fprintf(stderr,"APPKIT_LAYER_FAIL %d %s\n",__LINE__,#c);exit(1);}}while(0)
int main(void){setbuf(stdout,NULL);@autoreleasepool{
 NSView *view=[[NSView alloc]initWithFrame:NSMakeRect(0,0,8,8)];CHECK(view);CHECK(![view window]);
 [CATransaction begin];[CATransaction setDisableActions:YES];
 CALayer *layer=[CALayer layer];layer.frame=CGRectMake(0,0,8,8);CGColorRef red=CGColorCreateGenericRGB(1,0,0,1);layer.backgroundColor=red;
 [view setLayer:layer];CHECK([view layer]==layer);
 Ivar slot=class_getInstanceVariable([NSView class],"_layerContext");CHECK(slot);
 CALayerContext *context=object_getIvar(view,slot);CHECK([context isKindOfClass:NSClassFromString(@"CALayerContext")]);
 [context render];CGImageRef image=[context copyRenderedImage];CHECK(image&&CGImageGetWidth(image)==8&&CGImageGetHeight(image)==8);
 CFDataRef data=CGDataProviderCopyData(CGImageGetDataProvider(image));CHECK(data);const UInt8 *bytes=CFDataGetBytePtr(data);size_t row=CGImageGetBytesPerRow(image);unsigned count=0;
 for(unsigned y=0;y<8;y++)for(unsigned x=0;x<8;x++){const UInt8 *p=bytes+y*row+x*4;if(p[0]==255&&!p[1]&&!p[2]&&p[3]==255)count++;}CHECK(count==64);CFRelease(data);CGImageRelease(image);
 [view setFrameSize:NSMakeSize(11,9)];[context render];image=[context copyRenderedImage];CHECK(image&&CGImageGetWidth(image)==11&&CGImageGetHeight(image)==9);CGImageRelease(image);
 [view setLayer:nil];CHECK(![view layer]);CHECK(!object_getIvar(view,slot));
 [view setWantsLayer:YES];CHECK([view wantsLayer]&&[view layer]);CHECK(object_getIvar(view,slot));
 [view setWantsLayer:NO];CHECK(![view wantsLayer]&&![view layer]);CHECK(!object_getIvar(view,slot));
 [view release];CGColorRelease(red);[CATransaction commit];
 puts("REAL_DARLING_NSVIEW_HOSTED_AND_BACKING_LAYER_CONTEXT_PIXELS_RESIZE_AND_TEARDOWN_OK");return 0;
}}
