BITS 64
SECTION .text

; Export functions as global symbols for linking
GLOBAL _start  ; Entry point
GLOBAL FUNC_a
GLOBAL FUNC_b
GLOBAL FUNC_main
GLOBAL FUNC_print

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
FUNC_print:
    ; print syscall
    MOV RAX, 1  ; print (64-bit)
    SYSCALL
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_print) < 1024
times 1024 - ($ - FUNC_print) db 0x90
%endif

FUNC_a:
    ; Single call to b (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 2  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_a_0:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 0 (stored in single byte)
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_a) < 1024
times 1024 - ($ - FUNC_a) db 0x90
%endif

FUNC_b:
    LEA RAX, [rel GLOBAL_msg]  ; Load array address (PIC)
    MOV RSI, RAX  ; Buffer address
    MOV RDI, 1  ; stdout file descriptor
    MOV RDX, 13  ; String length (compile-time)
    ; Single call to print (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 0  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_b_1:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 1 (stored in single byte)
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_b) < 1024
times 1024 - ($ - FUNC_b) db 0x90
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
FOR_81:
    MOV RBX, RBX  ; Use i from register
    MOV EAX, R8D  ; Load iterations from register R8 (32-bit)
    CMP RBX, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ END_FOR_81
    ; Single call to a (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 1  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_2:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 2 (stored in single byte)
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    PUSH RAX  ; Save original value
    INC RAX
    MOV DWORD [RBP - 16], EAX  ; Store i
    MOV EBX, EAX  ; Update i in register RBX (32-bit)
    POP RAX  ; Return original value
    JMP FOR_81
END_FOR_81:
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

SECTION .text
GLOBAL_msg:
    DB 'H'
    DB 'e'
    DB 'l'
    DB 'l'
    DB 'o'
    DB ' '
    DB 'W'
    DB 'o'
    DB 'r'
    DB 'l'
    DB 'd'
    DB '!'
    DB 10  ; newline
    DB 0  ; null terminator
SECTION .data
