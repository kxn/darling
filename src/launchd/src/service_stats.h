#ifndef DARLING_LAUNCHD_SERVICE_STATS_H
#define DARLING_LAUNCHD_SERVICE_STATS_H
#include <stdbool.h>
#include <stdint.h>
#include <sys/types.h>
#include <xpc/xpc.h>

bool launchd_service_stats_demux(xpc_object_t request, xpc_object_t* reply);
void launchd_service_stats_record_exit(const char* label, uint64_t start_time,
	uint64_t unique_id, pid_t pid, int wait_status);
#endif
