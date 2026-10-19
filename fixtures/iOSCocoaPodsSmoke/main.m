#import <UIKit/UIKit.h>
#import <LocalMath/LocalMath.h>
@interface SmokeDelegate : UIResponder <UIApplicationDelegate>
@property (nonatomic, strong) UIWindow *window;
@end
@implementation SmokeDelegate
- (BOOL)application:(UIApplication *)application didFinishLaunchingWithOptions:(NSDictionary *)options {
    self.window = [[UIWindow alloc] initWithFrame:UIScreen.mainScreen.bounds];
    UIViewController *controller = [UIViewController new];
    controller.view.backgroundColor = UIColor.whiteColor;
    UILabel *label = [[UILabel alloc] initWithFrame:CGRectMake(20, 80, 300, 60)];
    label.text = [NSString stringWithFormat:@"Darling iOS CocoaPods: %d", local_add(20, 22)];
    [controller.view addSubview:label];
    self.window.rootViewController = controller;
    [self.window makeKeyAndVisible];
    return YES;
}
@end
int main(int argc, char **argv) {
    @autoreleasepool { return UIApplicationMain(argc, argv, nil, NSStringFromClass(SmokeDelegate.class)); }
}
