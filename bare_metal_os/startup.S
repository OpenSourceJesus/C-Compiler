; Bare Metal OS Startup Code
; Assembly entry point and low-level initialization

SECTION .text

; Global symbols for C code
GLOBAL _start
GLOBAL interrupt_handler_asm
GLOBAL kernel_entry

; Entry point - called by bootloader or directly
_start:
    ; Set up stack pointer
    ; For bare metal, we need to set up our own stack
    MOV RSP, stack_top
    
    ; Clear direction flag (required for string operations)
    CLD
    
    ; Initialize segment registers (if needed)
    ; For 64-bit mode, most segment registers are ignored, but we set them anyway
    MOV AX, 0
    MOV DS, AX
    MOV ES, AX
    MOV FS, AX
    MOV GS, AX
    MOV SS, AX
    
    ; Call kernel entry point (C main function)
    CALL FUNC_main
    
    ; If main returns, halt the system
    HLT
    
    ; Infinite loop as fallback
halt_loop:
    JMP halt_loop

; Assembly wrapper for interrupt handler
interrupt_handler_asm:
    ; Save all registers
    PUSH RAX
    PUSH RBX
    PUSH RCX
    PUSH RDX
    PUSH RSI
    PUSH RDI
    PUSH RBP
    PUSH R8
    PUSH R9
    PUSH R10
    PUSH R11
    PUSH R12
    PUSH R13
    PUSH R14
    PUSH R15
    
    ; Call C interrupt handler
    CALL FUNC_interrupt_handler
    
    ; Restore all registers
    POP R15
    POP R14
    POP R13
    POP R12
    POP R11
    POP R10
    POP R9
    POP R8
    POP RBP
    POP RDI
    POP RSI
    POP RDX
    POP RCX
    POP RBX
    POP RAX
    
    ; Return from interrupt
    IRETQ

; Kernel entry point (alternative entry)
kernel_entry:
    ; Same as _start but can be called from other contexts
    MOV RSP, stack_top
    CLD
    CALL FUNC_main
    HLT
    JMP kernel_entry

SECTION .bss
; Stack space (8KB stack)
stack_bottom:
    RESB 8192
stack_top:

SECTION .data
; Kernel data section
kernel_magic:
    DQ 0x4B45524E454C00  ; "KERNEL\0" in ASCII
