#include <expected>
#include <cassert>
#include "expected-access-fixture.h"
static unsigned live;
extern "C" void expected_payload_acquire(){++live;}
extern "C" void expected_payload_release(){assert(live);--live;}
extern "C" unsigned expected_live_payloads(){return live;}
extern "C" int expected_valid_value(){std::expected<int,int> result(42);return result.value();}
extern "C" void expected_throw_int(){std::expected<int,int> result(std::unexpect,73);(void)result.value();}
extern "C" void expected_throw_payload(){std::expected<void,ExpectedPayload> result(std::unexpect,91);result.value();}
std::exception_ptr expected_saved_payload(){try{expected_throw_payload();}catch(...){return std::current_exception();}return {};}
