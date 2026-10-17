#pragma once
#include <exception>
extern "C" void expected_payload_acquire();
extern "C" void expected_payload_release();
struct ExpectedPayload {
    int code;
    unsigned long long marker;
    explicit ExpectedPayload(int n):code(n),marker(0xfedcba9876543210ULL){expected_payload_acquire();}
    ExpectedPayload(const ExpectedPayload& p):code(p.code),marker(p.marker){expected_payload_acquire();}
    ExpectedPayload(ExpectedPayload&& p):code(p.code),marker(p.marker){expected_payload_acquire();p.code=-1;}
    ~ExpectedPayload(){expected_payload_release();}
};
extern "C" void expected_throw_int();
extern "C" void expected_throw_payload();
std::exception_ptr expected_saved_payload();
extern "C" int expected_valid_value();
extern "C" unsigned expected_live_payloads();
