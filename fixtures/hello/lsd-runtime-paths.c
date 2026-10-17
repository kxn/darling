#include <dlfcn.h>
#include <errno.h>
#include <pwd.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
int main(int argc, char **argv) {
    setbuf(stdout, NULL);
    struct passwd *pw = getpwuid(getuid());
    printf("uid=%u HOME=%s passwd=%s home=%s\n", getuid(), getenv("HOME"), pw ? pw->pw_name : "<absent>", pw ? pw->pw_dir : "<absent>");
    void *h = dlopen(argv[1], RTLD_LAZY); if (!h) { puts(dlerror()); return 1; }
    char *(*f)(uid_t,int,char*,size_t) = dlsym(h,"__user_local_dirname");
    for (int i=0;i<4;i++) {
        char path[1024]; errno=0; char *p=f(getuid(),i,path,sizeof(path)); int e=errno;
        printf("USER_DIRECTORY %d %s errno=%d\n", i,p?p:"<absent>",e);
    }
    if (argc == 3) {
        unsigned failures = 0;
        char *(*initialize)(int,char*,size_t) = dlsym(h,"_dirhelper");
        if (!initialize) return 2;
        for (int i=0;i<3;i++) {
            char path[1024]; errno=0; char *p=initialize(i,path,sizeof(path)); int e=errno;
            printf("INITIALIZED_USER_DIRECTORY %d %s errno=%d\n",i,p?p:"<absent>",e);
            struct stat st;
            if (!p || stat(p, &st) || !S_ISDIR(st.st_mode)) failures++;
        }
        if (failures) return 1;
        puts("ORIGINAL_DIRHELPER_THREE_REAL_USER_DIRECTORIES_CREATED_OK");
    }
}
