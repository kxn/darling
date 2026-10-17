// Launchd exit records collected from actual wait4 results, using the native
// launch-control envelope and packed shared-memory record ABI.
#include "service_stats.h"
#include <xpc/private.h>
#include <xpc/private/launch_service_stats.h>
#include <mach/mach_vm.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <sys/mman.h>
#include <unistd.h>

_Static_assert(sizeof(struct launch_service_stats_record) == 59, "native record ABI");

struct stored_record {
	struct launch_service_stats_record record;
	char* label;
};
struct monitor {
	struct monitor* next;
	char* name;
	uint32_t capacity, head, count, dropped;
	struct stored_record* records;
};
static struct monitor* monitors;

static struct monitor** find_monitor(const char* name) {
	struct monitor** at = &monitors;
	while (*at && strcmp((*at)->name, name)) at = &(*at)->next;
	return at;
}
static void clear_monitor(struct monitor* monitor) {
	for (uint32_t i = 0; i < monitor->capacity; ++i) {
		free(monitor->records[i].label); monitor->records[i].label = NULL;
	}
	monitor->head = monitor->count = monitor->dropped = 0;
}
static int enable_monitor(const char* name, uint64_t capacity) {
	if (*find_monitor(name)) return EEXIST;
	if (!capacity || capacity > (1U << 20)) return EINVAL;
	unsigned active = 0;
	for (struct monitor* p = monitors; p; p = p->next) ++active;
	if (active >= 32) return ENOSPC;
	struct monitor* monitor = calloc(1, sizeof(*monitor));
	if (!monitor) return ENOMEM;
	monitor->name = strdup(name);
	monitor->records = calloc(capacity, sizeof(*monitor->records));
	if (!monitor->name || !monitor->records) {
		free(monitor->name); free(monitor->records); free(monitor); return ENOMEM;
	}
	monitor->capacity = capacity; monitor->next = monitors; monitors = monitor;
	return 0;
}
static int disable_monitor(const char* name) {
	struct monitor** at = find_monitor(name);
	if (!*at) return ENOENT;
	struct monitor* monitor = *at; *at = monitor->next;
	clear_monitor(monitor);
	free(monitor->records); free(monitor->name); free(monitor);
	return 0;
}

void launchd_service_stats_record_exit(const char* label, uint64_t start_time,
		uint64_t unique_id, pid_t pid, int wait_status) {
	if (!label || pid <= 0 || !start_time) return;
	for (struct monitor* monitor = monitors; monitor; monitor = monitor->next) {
		char* name = strdup(label);
		if (!name) { ++monitor->dropped; continue; }
		if (monitor->count == monitor->capacity) {
			free(monitor->records[monitor->head].label);
			monitor->records[monitor->head].label = NULL;
			monitor->head = (monitor->head + 1) % monitor->capacity;
			--monitor->count; ++monitor->dropped;
		}
		uint32_t index = (monitor->head + monitor->count++) % monitor->capacity;
		struct stored_record* stored = &monitor->records[index];
		memset(&stored->record, 0, sizeof(stored->record));
		stored->label = name;
		stored->record.start_time = start_time;
		stored->record.unique_id = unique_id;
		stored->record.pid = pid;
		stored->record.wait_status = (uint32_t)wait_status;
		// Darwin OS_REASON_SIGNAL namespace is 2. Wait status is the real
		// source here; do not invent jetsam or code-signing exit reasons.
		if (WIFSIGNALED(wait_status)) {
			stored->record.reason_namespace = 2;
			stored->record.reason_code = WTERMSIG(wait_status);
		}
		// Later per-platform fields have no provider in this backend yet.
		// They remain zero; neither resource metrics nor jetsam are claimed.
	}
}

static int copy_monitor(struct monitor* monitor, xpc_object_t request, xpc_object_t reply) {
	xpc_object_t shmem = xpc_dictionary_get_value(request, "shmem");
	if (xpc_get_type(shmem) != XPC_TYPE_SHMEM) return EINVAL;
	void* buffer = NULL;
	size_t length = xpc_shmem_map(shmem, &buffer);
	if (!length || length < (size_t)getpagesize()) return EINVAL;
	int error = 0;
	if (mach_vm_protect(mach_task_self(), (mach_vm_address_t)buffer, length, FALSE,
			VM_PROT_READ | VM_PROT_WRITE) != KERN_SUCCESS) { error = EACCES; goto out; }
	xpc_object_t labels = xpc_array_create(NULL, 0);
	xpc_object_t indices = xpc_dictionary_create(NULL, NULL, 0);
	if (!labels || !indices) {
		if (labels) xpc_release(labels);
		if (indices) xpc_release(indices);
		error = ENOMEM; goto out;
	}
	uint32_t count = length / 59 < monitor->count ? length / 59 : monitor->count;
	// Native launchd returns the newest records that fit, then clears the
	// entire ring. This differs from draining the oldest subset in batches.
	uint32_t first = monitor->count - count;
	for (uint32_t i = 0; i < count; ++i) {
		struct stored_record* stored = &monitor->records[(monitor->head + first + i) % monitor->capacity];
		xpc_object_t existing = xpc_dictionary_get_value(indices, stored->label);
		uint32_t label_index;
		if (existing) label_index = (uint32_t)xpc_uint64_get_value(existing);
		else {
			label_index = (uint32_t)xpc_array_get_count(labels);
			xpc_object_t name = xpc_string_create(stored->label);
			xpc_array_append_value(labels, name); xpc_release(name);
			xpc_dictionary_set_uint64(indices, stored->label, label_index);
		}
		struct launch_service_stats_record record = stored->record;
		record.label_index = label_index;
		memcpy((char*)buffer + i * 59, &record, 59);
	}
	xpc_dictionary_set_uint64(reply, "count", count);
	xpc_dictionary_set_uint64(reply, "dropped-count", monitor->dropped);
	xpc_dictionary_set_value(reply, "labels", labels);
	xpc_release(labels); xpc_release(indices);
	clear_monitor(monitor);
out:
	munmap(buffer, length);
	return error;
}

bool launchd_service_stats_demux(xpc_object_t request, xpc_object_t* reply) {
	if (xpc_dictionary_get_uint64(request, "subsystem") != XPC_LAUNCH_STATS_SUBSYSTEM) return false;
	*reply = xpc_dictionary_create_reply(request);
	if (!*reply) return true;
	int error = 0;
	audit_token_t token;
	xpc_dictionary_get_audit_token(request, &token);
	// Native service statistics require a privileged entitlement. This
	// backend permits root and explicitly denies unprivileged callers.
	if (token.val[1] != 0 || !token.val[5] || token.val[5] == UINT32_MAX) error = EPERM;
	const char* name = xpc_dictionary_get_string(request, "monitor_id");
	if (!error && (!name || !*name || strlen(name) > 255)) error = EINVAL;
	if (!error) {
		struct monitor* monitor = *find_monitor(name);
		switch (xpc_dictionary_get_uint64(request, "routine")) {
		case XPC_LAUNCH_STATS_ENABLE:
			error = enable_monitor(name, xpc_dictionary_get_uint64(request, "capacity")); break;
		case XPC_LAUNCH_STATS_DISABLE:
			error = disable_monitor(name); break;
		case XPC_LAUNCH_STATS_QUERY:
			xpc_dictionary_set_bool(*reply, "enabled", monitor != NULL); break;
		case XPC_LAUNCH_STATS_COPY:
			error = monitor ? copy_monitor(monitor, request, *reply) : ENOENT; break;
		default: error = ENOTSUP;
		}
	}
	if (error) xpc_dictionary_set_int64(*reply, "error", error);
	return true;
}
