// The Context2 API differs only in pointer authentication on arm64e.
// Swift's MetadataLookup.cpp delegates both APIs to the same implementation.
.text
.globl _swift_getTypeByMangledNameInContext2
.p2align 4
_swift_getTypeByMangledNameInContext2:
    jmp _swift_getTypeByMangledNameInContext
