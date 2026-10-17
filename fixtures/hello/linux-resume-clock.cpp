#include "LinuxResumeClock.h"
#include <cstdio>
#include <cstdlib>
#include <cstdint>
static unsigned checks;
static void check(bool b) { ++checks; if (!b) { std::fprintf(stderr,"clock check %u failed\n",checks); std::exit(1); } }
int main() {
    LinuxResumeClock clock;
    constexpr int64_t s=1000000000;
    check(!clock.observe(s,4*s,s+1000)); // Existing host uptime offset is not a resume.
    for(int i=2;i<1002;i++) check(!clock.observe(i*s,i*s+3*s,i*s+1000));
    check(clock.observe(1002*s,1007*s,1002*s+1000)); // Actual 2 s boottime-only advance.
    check(!clock.observe(1003*s,1008*s,1003*s+1000));
    check(!clock.observe(1004*s,1009*s,1004*s+30000000)); // Slow sample discarded.
    check(!clock.observe(1005*s,1010*s,1005*s+1000));
    check(!clock.observe(-1,0,0));
    check(!clock.observe(1006*s,1000*s,1006*s+1000));
    check(!clock.observe(1006*s,1011*s,1006*s-1));
    check(clock.observe(1006*s,1014*s,1006*s+1000));
    check(!clock.observe(1,5,2)); // Backward/reset clock establishes a fresh baseline.
    check(!clock.observe(3,7,4));
    LinuxResumeClock noisy;
    check(!noisy.observe(s,2*s,s+19000000));
    check(!noisy.observe(2*s,3*s+90000000,2*s+1000)); // Below observation threshold.
    check(noisy.observe(3*s,4*s+300000000,3*s+1000));
    LinuxResumeClock limits;
    check(!limits.observe(INT64_MAX-2,INT64_MAX,INT64_MAX-1));
    check(!limits.observe(INT64_MAX-1,INT64_MAX,INT64_MAX));
    std::printf("LINUX_RESUME_CLOCK checks=%u\n",checks);
}
