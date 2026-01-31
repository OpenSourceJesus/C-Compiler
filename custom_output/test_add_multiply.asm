BITS 64
SECTION .text

; Export functions as global symbols for linking
GLOBAL _start  ; Entry point
GLOBAL FUNC_add
GLOBAL FUNC_main
GLOBAL FUNC_multiply

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
FUNC_add:
    MOV RAX, RDI  ; Load parameter a
    MOV R10, RAX  ; Save left operand
    MOV RAX, RSI  ; Load parameter b
    ADD RAX, R10
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_add) < 1024
times 1024 - ($ - FUNC_add) db 0x90
%endif

FUNC_multiply:
    MOV RAX, RDI  ; Load parameter x
    MOV R10, RAX  ; Save left operand
    MOV RAX, RSI  ; Load parameter y
    MUL R10
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_multiply) < 1024
times 1024 - ($ - FUNC_multiply) db 0x90
%endif

FUNC_main:
    PUSH RBX  ; Callee-saved: preserve RBX
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
    SUB RSP, 8  ; Allocate stack space for result
    MOV RAX, 0
    MOV R9D, EAX  ; Initialize result in register R9 (32-bit)
    SUB RSP, 8  ; Allocate stack space for i
    MOV RAX, 0
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
FOR_60:
    MOV R10, RBX  ; Use i from register
    MOV EAX, R8D  ; Load iterations from register R8 (32-bit)
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ END_FOR_60
    SUB RSP, 8  ; Allocate stack space for result1
    MOV RAX, 3
    MOV RDI, RAX
    MOV RAX, 4
    MOV RSI, RAX
    ; Single call to add (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 0  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_0:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 0 (stored in single byte)
    MOV DWORD [RBP - 32], EAX  ; Store result1 (32-bit)
    SUB RSP, 8  ; Allocate stack space for result2
    MOV RAX, 5
    MOV RDI, RAX
    MOV RAX, 6
    MOV RSI, RAX
    ; Single call to multiply (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 1  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_1:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 1 (stored in single byte)
    MOV DWORD [RBP - 40], EAX  ; Store result2 (32-bit)
    MOV EAX, R9D  ; Load result from register R9 (32-bit)
    PUSH RAX  ; Save current value
    MOV EAX, DWORD [RBP - 32]  ; Load result1 (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 40]  ; Load result2 (32-bit)
    ADD RAX, R10
    POP R10  ; Get current value
    ADD RAX, R10
    MOV R9D, EAX  ; Store result to register R9 (32-bit)
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    PUSH RAX  ; Save original value
    INC RAX
    MOV DWORD [RBP - 24], EAX  ; Store i
    MOV EBX, EAX  ; Update i in register RBX (32-bit)
    POP RAX  ; Return original value
    JMP FOR_60
END_FOR_60:
    MOV R10, R9  ; Use result from register
    MOV RAX, 256
    ; Modulo operation: R10 % RAX
    PUSH RAX  ; Save right operand (divisor)
    MOV RAX, R10  ; Move left operand (dividend) to RAX
    POP R10  ; Get divisor
    XOR RDX, RDX  ; Clear RDX for division
    DIV R10  ; RAX = dividend / divisor, RDX = remainder
    MOV RAX, RDX  ; Remainder is the modulo result
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_main) < 1024
times 1024 - ($ - FUNC_main) db 0x90
%endif

SECTION .data

STACK_BASE:
    DQ 0x7FFF0000  ; Stack base address

