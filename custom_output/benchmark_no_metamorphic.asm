BITS 64
SECTION .text

; Export functions as global symbols for linking
GLOBAL _start  ; Entry point
GLOBAL FUNC_main

; Program entry point
_start:
    ; Align stack to 16 bytes (x86-64 ABI requirement)
    AND RSP, 0xFFFFFFFFFFFFFFF0  ; Align to 16-byte boundary
    CALL _init_simd_packing  ; Initialize SIMD bit-packing
    CALL FUNC_main  ; Call main function
    ; Main return value is in RAX, save it for exit
    MOV RDI, RAX  ; Save return value to RDI (exit code)
    ; Exit system call (sys_exit)
    MOV RAX, 60  ; sys_exit
    SYSCALL

; Co-located small functions (<1024 bytes) in 1024-byte slots
ALIGN 1024
SMALL_FUNC_BASE:
FUNC_main:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 24  ; Allocate stack for all locals
    MOV RAX, 1000000
    MOV R8D, EAX  ; Initialize iterations in register R8 (32-bit)
    MOV RAX, 0
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
FOR_34:
    MOV R10, RBX  ; Use i from register
    MOV EAX, R8D  ; Load iterations from register R8 (32-bit)
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ END_FOR_34
    MOV RAX, 5000
    MOV BYTE [GLOBAL_a], AL  ; Store to packed variable
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    PUSH RAX  ; Save original value
    INC RAX
    MOV DWORD [RBP - 16], EAX  ; Store i
    MOV EBX, EAX  ; Update i in register RBX (32-bit)
    POP RAX  ; Return original value
    JMP FOR_34
END_FOR_34:
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

; SIMD Bit-Packing: Pack global variables (1-8 bits) into last SIMD register
; This register (xmm15) is typically ignored by standard compilers
; Variables declared as 'auto _Alignas(N) char' are packed as N-bit values
_init_simd_packing:
    ; Initialize xmm15 with packed global variables
    PXOR xmm15, xmm15  ; Clear register
    ; Pack a at bit 0, width 8 bits
    MOVZX RAX, BYTE [GLOBAL_a]  ; Load a
    ; Extract and mask to 8 bits
    AND RAX, 255  ; Mask to 8 bits
    MOVQ XMM0, RAX  ; Move to XMM0
    POR xmm15, XMM0  ; OR into packed register
    ; xmm15 now contains all packed global variables
    RET


SECTION .data

STACK_BASE:
    DQ 0x7FFF0000  ; Stack base address

GLOBAL_a:
    DB 0  ; a (packed into SIMD register)
