#!/usr/bin/env python3
"""Generate x86_64 tail-call stubs without re-declaring private CM signatures.

CM's selected entries take scalar/pointer/aggregate arguments. Preserve the
seven argument/vararg GP registers, eight XMM argument registers, stack arguments
and sret pointer across the resolver. Return values come straight from Apple.
AVX-width argument preservation is not claimed for arbitrary future APIs.
"""
import re
from pathlib import Path
root=Path(__file__).resolve().parent.parent
source=(root/'scripts/container-manager-native-loader.c').read_text()
names=re.findall(r'"(container_[a-z0-9_]+)"',source);assert len(names)==17
lines=['.text']
for i,name in enumerate(names):
 lines+=['.p2align 4, 0x90','.globl _'+name,'_'+name+':']
 lines+=['  pushq %'+r for r in ['rax','rdi','rsi','rdx','rcx','r8','r9']]
 lines+=['  subq $128, %rsp']
 lines+=['  movdqu %xmm'+str(n)+', '+str(16*n)+'(%rsp)' for n in range(8)]
 lines+=['  movl $'+str(i)+', %edi','  callq _linuxcode_container_manager_original_address','  movq %rax, %r11']
 lines+=['  movdqu '+str(16*n)+'(%rsp), %xmm'+str(n) for n in range(8)]
 lines+=['  addq $128, %rsp']
 lines+=['  popq %'+r for r in ['r9','r8','rcx','rdx','rsi','rdi','rax']]
 lines+=['  jmpq *%r11']
path=root/'runtime/container-manager-export/trampolines.S';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('\n'.join(lines)+'\n')
print('Generated 17 x86_64 scalar/aggregate register-preserving tail calls')
