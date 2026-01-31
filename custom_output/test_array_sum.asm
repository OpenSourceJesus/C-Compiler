BITS 64
SECTION .text

; Export functions as global symbols for linking
GLOBAL _start  ; Entry point
GLOBAL FUNC_main
GLOBAL FUNC_test_sum

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
FUNC_test_sum:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 8  ; Allocate stack space for sum
    MOV RAX, 0
    MOV R9D, EAX  ; Initialize sum in register R9 (32-bit)
    SUB RSP, 8  ; Allocate stack space for i
    MOV RAX, 0
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
FOR_34:
    MOV R10, RBX  ; Use i from register
    MOV RAX, RSI  ; Load parameter length
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ END_FOR_34
    MOV EAX, R9D  ; Load sum from register R9 (32-bit)
    PUSH RAX  ; Save current value
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Load parameter a
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    POP R10  ; Get current value
    ADD RAX, R10
    MOV R9D, EAX  ; Store sum to register R9 (32-bit)
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    PUSH RAX  ; Save original value
    INC RAX
    MOV DWORD [RBP - 16], EAX  ; Store i
    MOV EBX, EAX  ; Update i in register RBX (32-bit)
    POP RAX  ; Return original value
    JMP FOR_34
END_FOR_34:
    MOV EAX, R9D  ; Load sum from register R9 (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_sum) < 1024
times 1024 - ($ - FUNC_test_sum) db 0x90
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
    MOV RAX, 10
    MOV R8D, EAX  ; Initialize iterations in register R8 (32-bit)
    SUB RSP, 256  ; Allocate stack space for arr
    XOR RAX, RAX  ; Initialize arr to 0
    MOV DWORD [RBP - 264], EAX  ; Store arr (32-bit)
    SUB RSP, 8  ; Allocate stack space for i
    MOV RAX, 0
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
FOR_93:
    MOV R10, RBX  ; Use i from register
    MOV RAX, 64
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ END_FOR_93
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    PUSH RAX  ; Save value to assign
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    PUSH RAX  ; Save index
    LEA RBX, [RBP - 264]  ; Base address of local array
    POP RAX  ; Get index
    ; Array assignment: base + index * 4
    LEA RAX, [RBX + RAX*4]  ; base + index*4
    POP RCX  ; Get value to assign
    MOV DWORD [RAX], ECX  ; Store to array element
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    PUSH RAX  ; Save original value
    INC RAX
    MOV DWORD [RBP - 272], EAX  ; Store i
    MOV EBX, EAX  ; Update i in register RBX (32-bit)
    POP RAX  ; Return original value
    JMP FOR_93
END_FOR_93:
    SUB RSP, 8  ; Allocate stack space for i
    MOV RAX, 0
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
FOR_123:
    MOV R10, RBX  ; Use i from register
    MOV EAX, R8D  ; Load iterations from register R8 (32-bit)
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ END_FOR_123
    LEA RAX, [RBP - 264]  ; Array address
    MOV RDI, RAX
    MOV RAX, 64
    MOV RSI, RAX
    ; Single call to test_sum (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 0  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_0:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 0 (stored in single byte)
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    PUSH RAX  ; Save original value
    INC RAX
    MOV DWORD [RBP - 280], EAX  ; Store i
    MOV EBX, EAX  ; Update i in register RBX (32-bit)
    POP RAX  ; Return original value
    JMP FOR_123
END_FOR_123:
    MOV RAX, 0
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

