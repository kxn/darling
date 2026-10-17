#include <sys/stat.h>
int runnable_fixture_stat(const char *, struct stat *);
#define stat(...) runnable_fixture_stat(__VA_ARGS__)
#define macho_for_each_runnable_arch_name source_for_each_runnable_arch_name
