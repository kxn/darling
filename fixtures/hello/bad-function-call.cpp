#include <functional>
#include <cassert>
#include <cstring>
#include <cstdio>
#include <typeinfo>

int main() {
    std::function<int()> empty;
    bool caught=false;
    try { empty(); }
    catch (const std::bad_function_call &error) {
        assert(typeid(error)==typeid(std::bad_function_call));
        assert(error.what() && *error.what());
        std::printf("bad_function_call.what(): %s\n",error.what());
        std::bad_function_call copied(error);
        assert(std::strcmp(copied.what(),error.what())==0);
        caught=true;
    }
    assert(caught);
    std::function<int()> live=[] { return 42; };
    assert(live()==42);
    puts("REAL_BAD_FUNCTION_CALL_THROW_CATCH_COPY_WHAT_OK");
}
