// Test-only services live in this standalone harness, never the production daemon.
#include "IOService.h"
#include "ServiceRegistry.h"
#include "iokitd.h"
#import <Foundation/Foundation.h>
#include <dispatch/private.h>
#include <map>
#include <cstdio>
#include <cstdlib>
extern "C" {
#include "iokitmigServer.h"
void matching_client(mach_port_t master);
}
namespace {
class Fixture : public IOService {
public:
    explicit Fixture(int label):label(label) {}
    const char* className() const override { return "DarlingMatchingFixture"; }
    NSDictionary* matchingDictionary() override { return @{ @"IOProviderClass": @"DarlingMatchingFixture" }; }
    NSDictionary* getProperties() override { return @{ @"FixtureLabel": @(label), @"FixtureKind": @"test-only", @"FixturePayload": [NSString stringWithUTF8String:std::string(6000,'q').c_str()] }; }
    int label;
};
std::map<int,Fixture*> fixtures;
uint64_t create(int label) {
    auto* service=new Fixture(label);
    fixtures[label]=service;
    service->registerInPlane(kIOServicePlane,("Fixture-"+std::to_string(label)).c_str(),IORegistryEntry::root());
    ServiceRegistry::instance()->registerService(service);
    return service->id();
}
}
extern "C" uint64_t matching_fixture_create(int label) {
    __block uint64_t result=0;
    dispatch_sync(dispatch_get_main_queue(),^{result=create(label);});
    return result;
}
extern "C" void matching_fixture_republish(int label) {
    dispatch_sync(dispatch_get_main_queue(),^{ServiceRegistry::instance()->registerService(fixtures.at(label));});
}
extern "C" void matching_fixture_remove(int label) {
    dispatch_sync(dispatch_get_main_queue(),^{
        auto* service=fixtures.at(label);
        ServiceRegistry::instance()->unregisterService(service);
        fixtures.erase(label);
        service->release();
    });
}
extern "C" int matching_test_main(int argc,char** argv) {
    (void)argc;(void)argv;setbuf(stdout,nullptr);
    if(mach_port_allocate(mach_task_self(),MACH_PORT_RIGHT_RECEIVE,&g_masterPort)||
       mach_port_insert_right(mach_task_self(),g_masterPort,g_masterPort,MACH_MSG_TYPE_MAKE_SEND))return 1;
    IORegistryEntry::root();create(1);
    auto source=dispatch_source_create(DISPATCH_SOURCE_TYPE_MACH_RECV,g_masterPort,0,dispatch_get_main_queue());
    dispatch_source_set_event_handler(source,^{dispatch_mig_server(source,is_iokit_subsystem.maxsize,iokitSaveAuditTrail);});
    dispatch_resume(source);
    dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT,0),^{matching_client(g_masterPort);exit(0);});
    dispatch_main();return 0;
}
