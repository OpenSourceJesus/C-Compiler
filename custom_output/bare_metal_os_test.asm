BITS 32
SECTION .text

; Export functions as global symbols for linking
GLOBAL FUNC_create_task
GLOBAL FUNC_get_active_task
GLOBAL FUNC_get_tick_count
GLOBAL FUNC_interrupt_handler
GLOBAL FUNC_kernel_init
GLOBAL FUNC_kernel_tick
GLOBAL FUNC_main
GLOBAL FUNC_switch_task
GLOBAL FUNC_system_startup

; Co-located small functions (<1024 bytes) in 1024-byte slots
ALIGN 1024
SMALL_FUNC_BASE:
FUNC_kernel_init:
    MOV EAX, 1
    MOV [GLOBAL_kernel_initialized], EAX
    MOV EAX, 0
    MOV [GLOBAL_system_ready], EAX
    MOV EAX, 0
    MOV [GLOBAL_tick_count], EAX
    MOV EAX, 0
    MOV [GLOBAL_task_count], EAX
    MOV EAX, 0
    MOV [GLOBAL_active_task], EAX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_kernel_init) < 1024
times 1024 - ($ - FUNC_kernel_init) db 0x90
%endif

FUNC_system_startup:
    MOV EAX, [GLOBAL_kernel_initialized]  ; Load global variable
    NOT EAX
    TEST EAX, EAX
    JZ ELSE_35
    ; Single call to kernel_init (SMALL_FUNC_BASE + index*1024)
    MOV EBX, 0  ; Function index
    MOV EAX, SMALL_FUNC_BASE
    SHL EBX, 10  ; index * 1024
    ADD EAX, EBX
    CALL EAX  ; One call only
    ALIGN 16
RET_SITE_system_startup_0:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 0 (stored in single byte)
    JMP END_IF_35
ELSE_35:
END_IF_35:
    MOV EAX, 1
    MOV [GLOBAL_system_ready], EAX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_system_startup) < 1024
times 1024 - ($ - FUNC_system_startup) db 0x90
%endif

FUNC_kernel_tick:
    MOV EAX, [GLOBAL_system_ready]  ; Load global variable
    TEST EAX, EAX
    JZ ELSE_60
    MOV EAX, [GLOBAL_tick_count]  ; Load global variable
    MOV EAX, [GLOBAL_tick_count]
    PUSH EAX  ; Save original value
    INC EAX
    MOV [GLOBAL_tick_count], EAX
    POP EAX  ; Return original value
    JMP END_IF_60
ELSE_60:
END_IF_60:
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_kernel_tick) < 1024
times 1024 - ($ - FUNC_kernel_tick) db 0x90
%endif

FUNC_create_task:
    MOV EBX, EBX  ; Use task_count from register
    MOV EAX, 8
    CMP EBX, EAX
    SETL AL
    MOVZX EAX, AL
    TEST EAX, EAX
    JZ ELSE_79
    MOV EAX, [GLOBAL_task_count]  ; Load global variable
    MOV EAX, [GLOBAL_task_count]
    PUSH EAX  ; Save original value
    INC EAX
    MOV [GLOBAL_task_count], EAX
    POP EAX  ; Return original value
    MOV EAX, [GLOBAL_task_count]  ; Load global variable
    SUB EAX, 1
    POP EBX  ; Restore callee-saved RBX
    RET
    JMP END_IF_79
ELSE_79:
END_IF_79:
    MOV EAX, 1
    NEG EAX
    POP EBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_create_task) < 1024
times 1024 - ($ - FUNC_create_task) db 0x90
%endif

FUNC_switch_task:
    MOV EBX, EDI  ; Use task_id from register
    MOV EAX, 0
    CMP EAX, EBX
    SETGE AL
    MOVZX EAX, AL
    TEST EAX, EAX
    JZ ELSE_109
    MOV EBX, EDI  ; Use task_id from register
    MOV EAX, [GLOBAL_task_count]  ; Load global variable
    CMP EBX, EAX
    SETL AL
    MOVZX EAX, AL
    TEST EAX, EAX
    JZ ELSE_109
    MOV EAX, EDI  ; Load parameter task_id
    MOV [GLOBAL_active_task], EAX
    JMP END_IF_109
ELSE_109:
END_IF_109:
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_switch_task) < 1024
times 1024 - ($ - FUNC_switch_task) db 0x90
%endif

FUNC_get_active_task:
    MOV EAX, [GLOBAL_active_task]  ; Load global variable
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_get_active_task) < 1024
times 1024 - ($ - FUNC_get_active_task) db 0x90
%endif

FUNC_get_tick_count:
    MOV EAX, [GLOBAL_tick_count]  ; Load global variable
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_get_tick_count) < 1024
times 1024 - ($ - FUNC_get_tick_count) db 0x90
%endif

FUNC_interrupt_handler:
    ; Interrupt callback: using zero-latency SIMD register access
    ; xmm15 contains packed kernel flags (no memory reads)
    PUSH EBP  ; Save old frame pointer
    MOV EBP, ESP  ; Set new frame pointer
    SUB ESP, 8  ; Allocate stack space for SIMD register
    ; Single call to kernel_tick (SMALL_FUNC_BASE + index*1024)
    MOV EBX, 2  ; Function index
    MOV EAX, SMALL_FUNC_BASE
    SHL EBX, 10  ; index * 1024
    ADD EAX, EBX
    CALL EAX  ; One call only
    ALIGN 16
RET_SITE_interrupt_handler_1:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 1 (stored in single byte)
    MOV ESP, EBP
    POP EBP
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_interrupt_handler) < 1024
times 1024 - ($ - FUNC_interrupt_handler) db 0x90
%endif

FUNC_main:
    PUSH EBX  ; Callee-saved: preserve RBX
    PUSH EBP  ; Save old frame pointer
    MOV EBP, ESP  ; Set new frame pointer
    SUB ESP, 40  ; Allocate stack for all locals
    XOR EAX, EAX  ; Initialize task1 to 0
    MOV [EBP - 8], EAX  ; Store task1
    XOR EAX, EAX  ; Initialize task2 to 0
    MOV [EBP - 16], EAX  ; Store task2
    XOR EAX, EAX  ; Initialize task3 to 0
    MOV [EBP - 24], EAX  ; Store task3
    ; Single call to kernel_init (SMALL_FUNC_BASE + index*1024)
    MOV EBX, 0  ; Function index
    MOV EAX, SMALL_FUNC_BASE
    SHL EBX, 10  ; index * 1024
    ADD EAX, EBX
    CALL EAX  ; One call only
    ALIGN 16
RET_SITE_main_2:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 2 (stored in single byte)
    ; Single call to system_startup (SMALL_FUNC_BASE + index*1024)
    MOV EBX, 1  ; Function index
    MOV EAX, SMALL_FUNC_BASE
    SHL EBX, 10  ; index * 1024
    ADD EAX, EBX
    CALL EAX  ; One call only
    ALIGN 16
RET_SITE_main_3:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 3 (stored in single byte)
    ; Single call to create_task (SMALL_FUNC_BASE + index*1024)
    MOV EBX, 3  ; Function index
    MOV EAX, SMALL_FUNC_BASE
    SHL EBX, 10  ; index * 1024
    ADD EAX, EBX
    CALL EAX  ; One call only
    MOV [EBP - 8], EAX  ; Store task1
    ; Single call to create_task (SMALL_FUNC_BASE + index*1024)
    MOV EBX, 3  ; Function index
    MOV EAX, SMALL_FUNC_BASE
    SHL EBX, 10  ; index * 1024
    ADD EAX, EBX
    CALL EAX  ; One call only
    MOV [EBP - 16], EAX  ; Store task2
    ; Single call to create_task (SMALL_FUNC_BASE + index*1024)
    MOV EBX, 3  ; Function index
    MOV EAX, SMALL_FUNC_BASE
    SHL EBX, 10  ; index * 1024
    ADD EAX, EBX
    CALL EAX  ; One call only
    MOV [EBP - 24], EAX  ; Store task3
    MOV EAX, [EBP - 8]  ; Load task1
    MOV EDI, EAX
    ; Single call to switch_task (SMALL_FUNC_BASE + index*1024)
    MOV EBX, 4  ; Function index
    MOV EAX, SMALL_FUNC_BASE
    SHL EBX, 10  ; index * 1024
    ADD EAX, EBX
    CALL EAX  ; One call only
    ALIGN 16
RET_SITE_main_4:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 4 (stored in single byte)
    MOV EAX, [EBP - 16]  ; Load task2
    MOV EDI, EAX
    ; Single call to switch_task (SMALL_FUNC_BASE + index*1024)
    MOV EBX, 4  ; Function index
    MOV EAX, SMALL_FUNC_BASE
    SHL EBX, 10  ; index * 1024
    ADD EAX, EBX
    CALL EAX  ; One call only
    ALIGN 16
RET_SITE_main_5:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 5 (stored in single byte)
    MOV EAX, [EBP - 24]  ; Load task3
    MOV EDI, EAX
    ; Single call to switch_task (SMALL_FUNC_BASE + index*1024)
    MOV EBX, 4  ; Function index
    MOV EAX, SMALL_FUNC_BASE
    SHL EBX, 10  ; index * 1024
    ADD EAX, EBX
    CALL EAX  ; One call only
    ALIGN 16
RET_SITE_main_6:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 6 (stored in single byte)
    MOV EAX, 0
    MOV EBX, EAX  ; Initialize i in register EBX
FOR_256:
    MOV EBX, EBX  ; Use i from register
    MOV EAX, 1000000
    CMP EBX, EAX
    SETL AL
    MOVZX EAX, AL
    TEST EAX, EAX
    JZ END_FOR_256
    ; Single call to kernel_tick (SMALL_FUNC_BASE + index*1024)
    MOV EBX, 2  ; Function index
    MOV EAX, SMALL_FUNC_BASE
    SHL EBX, 10  ; index * 1024
    ADD EAX, EBX
    CALL EAX  ; One call only
    ALIGN 16
RET_SITE_main_7:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 7 (stored in single byte)
    MOV EAX, EBX  ; Load i from register EBX
    MOV EAX, EBX  ; Load i from register EBX
    PUSH EAX  ; Save original value
    INC EAX
    MOV DWORD [EBP - 32], EAX  ; Store i
    MOV EBX, EAX  ; Update i in register EBX
    POP EAX  ; Return original value
    JMP FOR_256
END_FOR_256:
    MOV EAX, 0
    XOR ECX, ECX  ; Reset stack index
    MOV ESP, EBP
    POP ECX  ; Restore stack index register
    POP EBX  ; Restore stack base register
    POP EBP
    POP EBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_main) < 1024
times 1024 - ($ - FUNC_main) db 0x90
%endif

SECTION .data

STACK_BASE:
    DD 0x7FFF0000  ; Stack base address (32-bit)

GLOBAL_kernel_initialized:
    DD 0  ; kernel_initialized
GLOBAL_system_ready:
    DD 0  ; system_ready
GLOBAL_tick_count:
    DD 0  ; tick_count
GLOBAL_task_count:
    DD 0  ; task_count
GLOBAL_active_task:
    DD 0  ; active_task
