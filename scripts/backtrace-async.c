/*
 * Copyright (c) 2007, 2008 Apple Inc. All rights reserved.
 *
 * @APPLE_LICENSE_HEADER_START@
 * 
 * This file contains Original Code and/or Modifications of Original Code
 * as defined in and that are subject to the Apple Public Source License
 * Version 2.0 (the 'License'). You may not use this file except in
 * compliance with the License. Please obtain a copy of the License at
 * http://www.opensource.apple.com/apsl/ and read it before using this
 * file.
 * 
 * The Original Code and all software distributed under the License are
 * distributed on an 'AS IS' basis, WITHOUT WARRANTY OF ANY KIND, EITHER
 * EXPRESS OR IMPLIED, AND APPLE HEREBY DISCLAIMS ALL SUCH WARRANTIES,
 * INCLUDING WITHOUT LIMITATION, ANY WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE, QUIET ENJOYMENT OR NON-INFRINGEMENT.
 * Please see the License for the specific language governing rights and
 * limitations under the License.
 * 
 * @APPLE_LICENSE_HEADER_END@
 */


#include <stddef.h>
#include <stdint.h>
#include <mach/vm_types.h>

extern unsigned int _thread_stack_async_pcs(vm_address_t *buffer, unsigned max,
		unsigned *nb, unsigned skip, void *startfp);

size_t backtrace_async(void** buffer, size_t size, uint32_t *task_id_ptr) {
	unsigned int num_frames;
	uint32_t task_id = _thread_stack_async_pcs((vm_address_t*)buffer, size, &num_frames, 1, NULL);
	while (num_frames >= 1 && buffer[num_frames-1] == NULL) num_frames -= 1;
	if (task_id_ptr) *task_id_ptr = task_id;
	return num_frames;
}
