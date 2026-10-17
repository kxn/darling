#include <errno.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <pthread.h>
#include <string.h>
#include <sys/stat.h>
#include <limits.h>
#include "dirhelper_priv.h"

static char* dir_suffix = NULL;
static pthread_mutex_t dir_suffix_lock = PTHREAD_MUTEX_INITIALIZER;

void _dirhelper_fork_child(void)
{
}

void _libcoreservices_fork_child(void)
{
	/**
	 * my god, threading is *incredibly* tricky when mixed with `fork()`!
	 * and the POSIX spec is so unclear about the behavior of mutexes when `fork()`ing
	 * and the macOS docs are no help
	 *
	 * the *only* viable resources i found was this commit in jemalloc:
	 * https://github.com/jemalloc/jemalloc/commit/0a4f5a7eea5e42292cea95fd30a88201c8d4a1ca
	 *
	 * basically, it *seems* that it's fine to reinitialize mutexes in the child---on macOS at least
	 * but i really wish the POSIX spec or macOS docs mentioned this kind of stuff!
	 *
	 * undefined behavior is really the **worst** behavior
	 */
	dir_suffix_lock = (pthread_mutex_t) PTHREAD_MUTEX_INITIALIZER;

	/**
	 * i checked on a real macOS system and confirmed this behavior:
	 * `fork()` does NOT reset the directory suffix
	 */
	//dir_suffix = NULL;
}

/* A successful directory query must name an existing directory. */
static int ensure_directory(const char *path)
{
	struct stat st;
	if (mkdir(path, 0700) != 0 && errno != EEXIST) return -1;
	if (stat(path, &st) != 0) return -1;
	if (!S_ISDIR(st.st_mode)) {errno = ENOTDIR; return -1;}
	return 0;
}

char* _dirhelper(int which, char* p, size_t limit)
{
	if (!p || !limit || which < 0 || which > DIRHELPER_USER_LOCAL_LAST) {
		errno = EINVAL; return NULL;
	}
	pthread_mutex_lock(&dir_suffix_lock);
	const char *base = NULL, *home = getenv("HOME");
	char cache[PATH_MAX];
	int cache_length = 0, error = 0;
	if (which == DIRHELPER_USER_LOCAL_TEMP) {
		base = getenv("TMPDIR");
		if (!base || !*base) base = "/tmp";
	} else if (which == DIRHELPER_USER_LOCAL_CACHE) {
		if (home && *home) {
			cache_length = snprintf(cache, sizeof(cache), "%s/.cache", home);
			base = cache;
		} else base = "/tmp";
	} else base = home && *home ? home : "";
	if (cache_length < 0 || (size_t)cache_length >= sizeof(cache)) error = ENAMETOOLONG;
	else {
		int length = snprintf(p, limit, "%s/%s%s", base,
			dir_suffix ? dir_suffix : "", dir_suffix ? "/" : "");
		if (length < 0 || (size_t)length >= limit) error = ENAMETOOLONG;
		/* Service clients use a single mkdir for the suffix. Prepare its cache
			* base as well, including when the guest home has never had a cache. */
		else if ((home && *home && which != DIRHELPER_USER_LOCAL_TEMP &&
				ensure_directory(home) != 0) ||
			(cache_length && ensure_directory(cache) != 0) ||
			ensure_directory(p) != 0) error = errno;
	}
	pthread_mutex_unlock(&dir_suffix_lock);
	if (error) {errno = error; return NULL;}
	return p;
}

int _set_user_dir_suffix(const char* suffix)
{
	char *copy = suffix ? strdup(suffix) : NULL;
	if (suffix && !copy) return 0;
	pthread_mutex_lock(&dir_suffix_lock);
	free(dir_suffix);
	dir_suffix = copy;
	pthread_mutex_unlock(&dir_suffix_lock);
	return 1;
}
