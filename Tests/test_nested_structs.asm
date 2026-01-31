BITS 64
SECTION .text

; Export functions as global symbols for linking
GLOBAL _start  ; Entry point
GLOBAL FUNC_main
GLOBAL FUNC_test_func1
GLOBAL FUNC_test_func2
GLOBAL FUNC_test_func3
GLOBAL FUNC_test_func4
GLOBAL FUNC_test_func5
GLOBAL FUNC_test_func6
GLOBAL FUNC_test_func7

; Program entry point
_start:
    ; Align stack to 16 bytes (x86-64 ABI requirement)
    AND RSP, 0xFFFFFFFFFFFFFFF0  ; Align to 16-byte boundary
    CALL FUNC_main  ; Call main function
    ; Main return value is in RAX, save it for exit
    MOV RDI, RAX  ; Save return value to RDI (exit code)
    ; Exit system call (sys_exit)
    MOV RAX, 60  ; sys_exit
    SYSCALL

; Co-located small functions (<1024 bytes) in 1024-byte slots
ALIGN 1024
SMALL_FUNC_BASE:
FUNC_test_func1:
    ; Optimized nested struct access: container + 8
    MOV RAX, [GLOBAL_container + 8]  ; Load member with offset
    TEST RAX, RAX
    JZ ELSE_29
    ; Function pointer already in RAX from condition
    MOV RBX, RAX  ; Save function pointer
    ; Argument 1 (x) already in RDI
    MOV RAX, RBX  ; Restore function pointer
    JMP RAX  ; Call function pointer
ELSE_29:
END_IF_29:
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_func1) < 1024
times 1024 - ($ - FUNC_test_func1) db 0x90
%endif

FUNC_test_func2:
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 8  ; Allocate stack space for val
    ; Optimized nested struct access: container + 0
    MOV RAX, [GLOBAL_container]  ; Load member directly
    MOV DWORD [RBP - 8], EAX  ; Store val (32-bit)
    ; Optimized nested struct access: container + 4
    MOV RAX, [GLOBAL_container + 4]  ; Load member with offset
    MOV DWORD [RBP - 8], EAX  ; Store val (32-bit)
    ; Optimized nested struct access: container + 16
    MOV RAX, [GLOBAL_container + 16]  ; Load member with offset
    TEST RAX, RAX
    JZ ELSE_61
    ; Optimized nested struct access: container + 24
    MOV RAX, [GLOBAL_container + 24]  ; Load member with offset
    TEST RAX, RAX
    JZ ELSE_61
    ; Optimized nested struct access: container + 24
    MOV RAX, [GLOBAL_container + 24]  ; Load member with offset
    MOV RBX, RAX  ; Save function pointer
    MOV EAX, DWORD [RBP - 8]  ; Load val (32-bit)
    MOV RDI, RAX  ; Argument 1
    MOV RAX, RBX  ; Restore function pointer
    JMP RAX  ; Call function pointer
    JMP END_IF_61
ELSE_61:
END_IF_61:
    MOV RSP, RBP  ; Restore stack pointer
    POP RBP  ; Restore frame pointer
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_func2) < 1024
times 1024 - ($ - FUNC_test_func2) db 0x90
%endif

FUNC_test_func3:
    ; Optimized nested struct access: container + 32
    MOV RAX, [GLOBAL_container + 32]  ; Load member with offset
    TEST RAX, RAX
    JZ ELSE_88
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 16  ; Allocate stack space for result
    ; Optimized nested struct access: container + 32
    MOV RAX, [GLOBAL_container + 32]  ; Load member with offset
    MOV RBX, RAX  ; Save function pointer
    MOV RAX, RBX  ; Restore function pointer
    JMP RAX  ; Call function pointer
    MOV EBX, EAX  ; Initialize result in register RBX (32-bit)
    LEA RAX, [RBP - 16]  ; Base address of local struct result
    ; Struct member access: callback at offset 8
    ADD RAX, 8  ; Add member offset
    MOV RAX, [RAX]  ; Load member value
    TEST RAX, RAX
    JZ ELSE_106
    ; Function pointer already in RAX from condition
    MOV RBX, RAX  ; Save function pointer
    LEA RAX, [RBP - 16]  ; Base address of local struct result
    ; Struct member access: x at offset 0
    MOV RAX, [RAX]  ; Load member value
    MOV RDI, RAX  ; Argument 1
    MOV RAX, RBX  ; Restore function pointer
    JMP RAX  ; Call function pointer
ELSE_106:
END_IF_106:
    JMP END_IF_88
ELSE_88:
END_IF_88:
    MOV RSP, RBP  ; Restore stack pointer
    POP RBP  ; Restore frame pointer
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_func3) < 1024
times 1024 - ($ - FUNC_test_func3) db 0x90
%endif

FUNC_test_func4:
    ; Optimized nested struct access: container + 40
    MOV RAX, [GLOBAL_container + 40]  ; Load member with offset
    TEST RAX, RAX
    JZ ELSE_134
    ; Optimized nested struct access: container + 16
    MOV RAX, [GLOBAL_container + 16]  ; Load member with offset
    TEST RAX, RAX
    JZ ELSE_134
    ; Optimized nested struct access: container + 40
    MOV RAX, [GLOBAL_container + 40]  ; Load member with offset
    MOV RBX, RAX  ; Save function pointer
    ; Optimized nested struct access: container + 16
    MOV RAX, [GLOBAL_container + 16]  ; Load member with offset
    MOV RDI, RAX  ; Argument 1
    MOV RAX, RBX  ; Restore function pointer
    JMP RAX  ; Call function pointer
    JMP END_IF_134
ELSE_134:
END_IF_134:
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_func4) < 1024
times 1024 - ($ - FUNC_test_func4) db 0x90
%endif

FUNC_test_func5:
    ; Optimized nested struct access: container + 0
    MOV RAX, [GLOBAL_container]  ; Load member directly
    TEST RAX, RAX
    JZ ELSE_160
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 16  ; Allocate stack space for result
    ; Optimized nested struct access: container + 0
    MOV RAX, [GLOBAL_container]  ; Load member directly
    MOV RBX, RAX  ; Save function pointer
    ; Optimized nested struct access: container + 0
    MOV RAX, [GLOBAL_container]  ; Load member directly
    MOV RDI, RAX  ; Argument 1
    MOV RAX, RBX  ; Restore function pointer
    JMP RAX  ; Call function pointer
    MOV EBX, EAX  ; Initialize result in register RBX (32-bit)
    LEA RAX, [RBP - 16]  ; Base address of local struct result
    ; Struct member access: callback at offset 8
    ADD RAX, 8  ; Add member offset
    MOV RAX, [RAX]  ; Load member value
    TEST RAX, RAX
    JZ ELSE_181
    ; Function pointer already in RAX from condition
    MOV RBX, RAX  ; Save function pointer
    LEA RAX, [RBP - 16]  ; Base address of local struct result
    ; Struct member access: x at offset 0
    MOV RAX, [RAX]  ; Load member value
    PUSH RBX  ; Save result in RBX
    MOV RBX, RAX  ; Save left operand
    LEA RAX, [RBP - 16]  ; Base address of local struct result
    ; Struct member access: y at offset 4
    ADD RAX, 4  ; Add member offset
    MOV RAX, [RAX]  ; Load member value
    ADD RAX, RBX
    POP RBX  ; Restore RBX
    MOV RDI, RAX  ; Argument 1
    MOV RAX, RBX  ; Restore function pointer
    JMP RAX  ; Call function pointer
ELSE_181:
END_IF_181:
    JMP END_IF_160
ELSE_160:
END_IF_160:
    MOV RSP, RBP  ; Restore stack pointer
    POP RBP  ; Restore frame pointer
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_func5) < 1024
times 1024 - ($ - FUNC_test_func5) db 0x90
%endif

FUNC_test_func6:
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 16  ; Allocate stack space for handlers
    XOR RAX, RAX  ; Initialize handlers to 0
    MOV DWORD [RBP - 16], EAX  ; Store handlers (32-bit)
    SUB RSP, 8  ; Allocate stack space for i
    MOV RAX, 5
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    LEA RAX, [RBP - 16 + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    ; Struct member access: callback at offset 8
    ADD RAX, 8  ; Add member offset
    MOV RAX, [RAX]  ; Load member value
    TEST RAX, RAX
    JZ ELSE_230
    ; Function pointer already in RAX from condition
    MOV RBX, RAX  ; Save function pointer
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RDI, RAX  ; Argument 1
    MOV RAX, RBX  ; Restore function pointer
    JMP RAX  ; Call function pointer
ELSE_230:
END_IF_230:
    MOV RSP, RBP  ; Restore stack pointer
    POP RBP  ; Restore frame pointer
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_func6) < 1024
times 1024 - ($ - FUNC_test_func6) db 0x90
%endif

FUNC_test_func7:
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 8  ; Allocate stack space for deep1
    XOR EBX, EBX  ; Initialize deep1 to 0 in register RBX (32-bit)
    LEA RAX, [RBP - 8]  ; Base address of local struct deep1
    ; Struct member access: deep2 at offset 0
    MOV RAX, [RAX]  ; Load member value
    ; Struct member access: deep3 at offset 0
    MOV RAX, [RAX]  ; Load member value
    ; Struct member access: deep_callback at offset 0
    MOV RAX, [RAX]  ; Load member value
    TEST RAX, RAX
    JZ ELSE_265
    ; Function pointer already in RAX from condition
    MOV RBX, RAX  ; Save function pointer
    LEA RAX, [RBP - 8]  ; Base address of local struct deep1
    ; Struct member access: deep2 at offset 0
    MOV RAX, [RAX]  ; Load member value
    ; Struct member access: deep3 at offset 0
    MOV RAX, [RAX]  ; Load member value
    ; Struct member access: value at offset 24
    ADD RAX, 24  ; Add member offset
    MOV RAX, [RAX]  ; Load member value
    MOV RDI, RAX  ; Argument 1
    MOV RAX, RBX  ; Restore function pointer
    JMP RAX  ; Call function pointer
ELSE_265:
END_IF_265:
    LEA RAX, [RBP - 8]  ; Base address of local struct deep1
    ; Struct member access: deep2 at offset 0
    MOV RAX, [RAX]  ; Load member value
    ; Struct member access: deep3_ptr at offset 0
    MOV RAX, [RAX]  ; Load member value
    TEST RAX, RAX
    JZ ELSE_289
    LEA RAX, [RBP - 8]  ; Base address of local struct deep1
    ; Struct member access: deep2 at offset 0
    MOV RAX, [RAX]  ; Load member value
    ; Struct member access: deep3_ptr at offset 0
    MOV RAX, [RAX]  ; Load member value
    ; Struct member access: deep_callback at offset 0
    MOV RAX, [RAX]  ; Load member value
    TEST RAX, RAX
    JZ ELSE_289
    LEA RAX, [RBP - 8]  ; Base address of local struct deep1
    ; Struct member access: deep2 at offset 0
    MOV RAX, [RAX]  ; Load member value
    ; Struct member access: deep3_ptr at offset 0
    MOV RAX, [RAX]  ; Load member value
    ; Struct member access: deep_callback at offset 0
    MOV RAX, [RAX]  ; Load member value
    MOV RBX, RAX  ; Save function pointer
    LEA RAX, [RBP - 8]  ; Base address of local struct deep1
    ; Struct member access: deep2 at offset 0
    MOV RAX, [RAX]  ; Load member value
    ; Struct member access: deep3_ptr at offset 0
    MOV RAX, [RAX]  ; Load member value
    ; Struct member access: value at offset 24
    ADD RAX, 24  ; Add member offset
    MOV RAX, [RAX]  ; Load member value
    MOV RDI, RAX  ; Argument 1
    MOV RAX, RBX  ; Restore function pointer
    JMP RAX  ; Call function pointer
    JMP END_IF_289
ELSE_289:
END_IF_289:
    MOV RSP, RBP  ; Restore stack pointer
    POP RBP  ; Restore frame pointer
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_func7) < 1024
times 1024 - ($ - FUNC_test_func7) db 0x90
%endif

FUNC_main:
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 8  ; Allocate stack space for iterations
    MOV RAX, 1000000
    MOV R8D, EAX  ; Initialize iterations in register R8 (32-bit)
    SUB RSP, 8  ; Allocate stack space for i
    MOV RAX, 0
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
FOR_346:
    MOV RBX, RBX  ; Use i from register
    MOV EAX, R8D  ; Load iterations from register R8 (32-bit)
    CMP RBX, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ END_FOR_346
    MOV RAX, 1
    MOV RDI, RAX
    ; Single call to test_func1 (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 0  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_0:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 0 (stored in single byte)
    ; Single call to test_func2 (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 1  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_1:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 1 (stored in single byte)
    ; Single call to test_func3 (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 2  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_2:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 2 (stored in single byte)
    ; Single call to test_func4 (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 3  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_3:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 3 (stored in single byte)
    ; Single call to test_func5 (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 4  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_4:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 4 (stored in single byte)
    ; Single call to test_func6 (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 5  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_5:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 5 (stored in single byte)
    ; Single call to test_func7 (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 6  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_6:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 6 (stored in single byte)
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    PUSH RAX  ; Save original value
    INC RAX
    MOV DWORD [RBP - 16], EAX  ; Store i
    MOV EBX, EAX  ; Update i in register RBX (32-bit)
    POP RAX  ; Return original value
    JMP FOR_346
END_FOR_346:
    MOV RAX, 0
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_main) < 1024
times 1024 - ($ - FUNC_main) db 0x90
%endif

SECTION .data

STACK_BASE:
    DQ 0x7FFF0000  ; Stack base address

GLOBAL_x:
    DD 0  ; x
GLOBAL_y:
    DD 0  ; y
GLOBAL_callback:
    DD 0  ; callback
GLOBAL_inner:
    DD 0  ; inner
GLOBAL_inner_ptr:
    DD 0  ; inner_ptr
GLOBAL_value:
    DD 0  ; value
GLOBAL_get_inner:
    DD 0  ; get_inner
GLOBAL_handler:
    DD 0  ; handler
GLOBAL_outer:
    DD 0  ; outer
GLOBAL_outer_ptr:
    DD 0  ; outer_ptr
GLOBAL_nested:
    DD 0  ; nested
GLOBAL_func_ptr:
    DD 0  ; func_ptr
GLOBAL_container:
    DD 0  ; container
