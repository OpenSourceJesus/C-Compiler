BITS 64
SECTION .text

; Export functions as global symbols for linking
GLOBAL _start  ; Entry point
GLOBAL FUNC_cube
GLOBAL FUNC_main
GLOBAL FUNC_square
GLOBAL FUNC_sum_of_squares

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
FUNC_square:
    MOV R10, RDI  ; Use x from register
    MOV RAX, RDI  ; Load parameter x
    MUL R10
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_square) < 1024
times 1024 - ($ - FUNC_square) db 0x90
%endif

FUNC_cube:
    MOV R10, RDI  ; Use x from register
    MOV RAX, RDI  ; Load parameter x
    MUL R10
    MOV R10, RAX  ; Save left operand
    MOV RAX, RDI  ; Load parameter x
    MUL R10
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_cube) < 1024
times 1024 - ($ - FUNC_cube) db 0x90
%endif

FUNC_sum_of_squares:
    MOV RAX, RDI  ; Load parameter a
    MOV RDI, RAX
    ; Single call to square (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 0  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    MOV R10, RAX  ; Save left operand
    MOV RAX, RSI  ; Load parameter b
    MOV RDI, RAX
    ; Single call to square (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 0  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ADD RAX, R10
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_sum_of_squares) < 1024
times 1024 - ($ - FUNC_sum_of_squares) db 0x90
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
    SUB RSP, 72  ; Allocate stack for all locals
    MOV RAX, 1000000
    MOV R8D, EAX  ; Initialize iterations in register R8 (32-bit)
    MOV RAX, 0
    MOV R9D, EAX  ; Initialize result in register R9 (32-bit)
    MOV RAX, 0
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
FOR_86:
    MOV R10, RBX  ; Use i from register
    MOV EAX, R8D  ; Load iterations from register R8 (32-bit)
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ END_FOR_86
    MOV RAX, 3
    MOV DWORD [RBP - 32], EAX  ; Store a (32-bit)
    MOV RAX, 4
    MOV DWORD [RBP - 40], EAX  ; Store b (32-bit)
    MOV EAX, DWORD [RBP - 32]  ; Load a (32-bit)
    MOV RDI, RAX
    ; Single call to square (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 0  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    MOV DWORD [RBP - 48], EAX  ; Store sq (32-bit)
    MOV RAX, 2
    MOV RDI, RAX
    ; Single call to cube (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 1  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    MOV DWORD [RBP - 56], EAX  ; Store cb (32-bit)
    MOV EAX, DWORD [RBP - 32]  ; Load a (32-bit)
    MOV RDI, RAX
    MOV EAX, DWORD [RBP - 40]  ; Load b (32-bit)
    MOV RSI, RAX
    ; Single call to sum_of_squares (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 2  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    MOV DWORD [RBP - 64], EAX  ; Store sos (32-bit)
    MOV EAX, R9D  ; Load result from register R9 (32-bit)
    PUSH RAX  ; Save current value
    MOV EAX, DWORD [RBP - 48]  ; Load sq (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 56]  ; Load cb (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 64]  ; Load sos (32-bit)
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
    JMP FOR_86
END_FOR_86:
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

