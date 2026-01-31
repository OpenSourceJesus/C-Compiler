BITS 64
SECTION .text

; Export functions as global symbols for linking
GLOBAL _start  ; Entry point
GLOBAL FUNC_abs_value
GLOBAL FUNC_add
GLOBAL FUNC_bitwise_and
GLOBAL FUNC_bitwise_combined
GLOBAL FUNC_bitwise_not
GLOBAL FUNC_bitwise_or
GLOBAL FUNC_bitwise_xor
GLOBAL FUNC_classify_number
GLOBAL FUNC_clear_bits
GLOBAL FUNC_compare_values
GLOBAL FUNC_count_even
GLOBAL FUNC_count_matching
GLOBAL FUNC_divide
GLOBAL FUNC_extract_bits
GLOBAL FUNC_factorial
GLOBAL FUNC_fibonacci
GLOBAL FUNC_find_max
GLOBAL FUNC_find_min
GLOBAL FUNC_find_value
GLOBAL FUNC_generic_interrupt_handler
GLOBAL FUNC_get_point_x
GLOBAL FUNC_get_point_y
GLOBAL FUNC_init_array
GLOBAL FUNC_init_point
GLOBAL FUNC_init_rectangle
GLOBAL FUNC_irq_keyboard_handler
GLOBAL FUNC_isr_timer_handler
GLOBAL FUNC_left_shift
GLOBAL FUNC_main
GLOBAL FUNC_matrix_sum
GLOBAL FUNC_max
GLOBAL FUNC_min
GLOBAL FUNC_modulo
GLOBAL FUNC_move_rectangle
GLOBAL FUNC_multiple_returns
GLOBAL FUNC_multiply
GLOBAL FUNC_nested_calls
GLOBAL FUNC_point_distance_squared
GLOBAL FUNC_point_in_rectangle
GLOBAL FUNC_power2
GLOBAL FUNC_power_of_2
GLOBAL FUNC_process_data
GLOBAL FUNC_rectangle_area
GLOBAL FUNC_resize_rectangle
GLOBAL FUNC_reverse_array
GLOBAL FUNC_right_shift
GLOBAL FUNC_set_bits
GLOBAL FUNC_set_point
GLOBAL FUNC_single_return
GLOBAL FUNC_subtract
GLOBAL FUNC_sum_array
GLOBAL FUNC_sum_array_elements
GLOBAL FUNC_sum_until_negative
GLOBAL FUNC_test_address_of
GLOBAL FUNC_test_array_comparisons
GLOBAL FUNC_test_array_logical
GLOBAL FUNC_test_array_modulo
GLOBAL FUNC_test_assignments
GLOBAL FUNC_test_binary_ops
GLOBAL FUNC_test_char_constants
GLOBAL FUNC_test_combined_operators
GLOBAL FUNC_test_complex_expression
GLOBAL FUNC_test_complex_expressions
GLOBAL FUNC_test_compound_assignment
GLOBAL FUNC_test_compound_bitwise
GLOBAL FUNC_test_declarations
GLOBAL FUNC_test_globals
GLOBAL FUNC_test_increment_decrement
GLOBAL FUNC_test_mixed_globals
GLOBAL FUNC_test_mixed_operations
GLOBAL FUNC_test_nested_ternary
GLOBAL FUNC_test_numeric_constants
GLOBAL FUNC_test_pointer_increment
GLOBAL FUNC_test_simd_packed
GLOBAL FUNC_test_struct_operations
GLOBAL FUNC_test_ternary
GLOBAL FUNC_test_ternary_with_ops
GLOBAL FUNC_test_unary_ops
GLOBAL FUNC_timer_callback
GLOBAL FUNC_toggle_bits

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
FUNC_sum_array_elements:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 24  ; Allocate stack for all locals
    MOV RAX, 0
    MOV R9D, EAX  ; Initialize sum in register R9 (32-bit)
    MOV RAX, 0
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
FOR_113:
    MOV R10, RBX  ; Use i from register
    MOV RAX, RSI  ; Load parameter len
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ END_FOR_113
    MOV R10, R9  ; Use sum from register
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter arr
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    ADD RAX, R10
    MOV R9D, EAX  ; Store sum to register R9 (32-bit)
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    ADD RAX, 1
    MOV EBX, EAX  ; Store i to register RBX (32-bit)
    JMP FOR_113
END_FOR_113:
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
%if ($ - FUNC_sum_array_elements) < 1024
times 1024 - ($ - FUNC_sum_array_elements) db 0x90
%endif

FUNC_find_max:
    MOV R10, RSI  ; Use len from register
    MOV RAX, 0
    CMP R10, RAX
    SETLE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_151
    MOV RAX, 0
    POP RBX  ; Restore callee-saved RBX
    RET
    JMP END_IF_151
ELSE_151:
END_IF_151:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 24  ; Allocate stack for all locals
    MOV RAX, 0
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter arr
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    MOV R10D, EAX  ; Initialize max in register R10 (32-bit)
    MOV RAX, 1
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
FOR_179:
    PUSH R10  ; Save max
    MOV R10, RBX  ; Use i from register
    MOV RAX, RSI  ; Load parameter len
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    POP R10  ; Restore temp
    TEST RAX, RAX
    JZ END_FOR_179
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter arr
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    PUSH R10  ; Save max
    MOV R10, RAX  ; Save left operand
    MOV EAX, R10D  ; Load max from register R10 (32-bit)
    CMP RAX, R10
    SETG AL
    MOVZX RAX, AL
    POP R10  ; Restore temp
    TEST RAX, RAX
    JZ ELSE_191
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter arr
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    MOV R10D, EAX  ; Store max to register R10 (32-bit)
    JMP END_IF_191
ELSE_191:
END_IF_191:
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    ADD RAX, 1
    MOV EBX, EAX  ; Store i to register RBX (32-bit)
    JMP FOR_179
END_FOR_179:
    MOV EAX, R10D  ; Load max from register R10 (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_find_max) < 1024
times 1024 - ($ - FUNC_find_max) db 0x90
%endif

FUNC_find_min:
    MOV R10, RSI  ; Use len from register
    MOV RAX, 0
    CMP R10, RAX
    SETLE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_234
    MOV RAX, 0
    POP RBX  ; Restore callee-saved RBX
    RET
    JMP END_IF_234
ELSE_234:
END_IF_234:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 24  ; Allocate stack for all locals
    MOV RAX, 0
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter arr
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    MOV R10D, EAX  ; Initialize min in register R10 (32-bit)
    MOV RAX, 1
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
FOR_262:
    PUSH R10  ; Save min
    MOV R10, RBX  ; Use i from register
    MOV RAX, RSI  ; Load parameter len
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    POP R10  ; Restore temp
    TEST RAX, RAX
    JZ END_FOR_262
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter arr
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    PUSH R10  ; Save min
    MOV R10, RAX  ; Save left operand
    MOV EAX, R10D  ; Load min from register R10 (32-bit)
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    POP R10  ; Restore temp
    TEST RAX, RAX
    JZ ELSE_274
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter arr
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    MOV R10D, EAX  ; Store min to register R10 (32-bit)
    JMP END_IF_274
ELSE_274:
END_IF_274:
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    ADD RAX, 1
    MOV EBX, EAX  ; Store i to register RBX (32-bit)
    JMP FOR_262
END_FOR_262:
    MOV EAX, R10D  ; Load min from register R10 (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_find_min) < 1024
times 1024 - ($ - FUNC_find_min) db 0x90
%endif

FUNC_reverse_array:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 24  ; Allocate stack for all locals
    MOV RAX, 0
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
    MOV RAX, RSI  ; Load parameter len
    SUB RAX, 1
    MOV R8D, EAX  ; Initialize j in register R8 (32-bit)
WHILE_331:
    MOV R10, RBX  ; Use i from register
    MOV EAX, R8D  ; Load j from register R8 (32-bit)
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ END_WHILE_331
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter arr
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    MOV DWORD [RBP - 24], EAX  ; Store temp (32-bit)
    MOV EAX, R8D  ; Load j from register R8 (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter arr
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    PUSH RAX  ; Save value to assign
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    PUSH RAX  ; Save index
    MOV RBX, RDI  ; Base from parameter arr
    POP RAX  ; Get index
    ; Array assignment: base + index * 4
    LEA RAX, [RBX + RAX*4]  ; base + index*4
    POP RCX  ; Get value to assign
    MOV DWORD [RAX], ECX  ; Store to array element
    MOV EAX, DWORD [RBP - 24]  ; Load temp (32-bit)
    PUSH RAX  ; Save value to assign
    MOV EAX, R8D  ; Load j from register R8 (32-bit)
    PUSH RAX  ; Save index
    MOV RBX, RDI  ; Base from parameter arr
    POP RAX  ; Get index
    ; Array assignment: base + index * 4
    LEA RAX, [RBX + RAX*4]  ; base + index*4
    POP RCX  ; Get value to assign
    MOV DWORD [RAX], ECX  ; Store to array element
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    ADD RAX, 1
    MOV EBX, EAX  ; Store i to register RBX (32-bit)
    MOV EAX, R8D  ; Load j from register R8 (32-bit)
    SUB RAX, 1
    MOV R8D, EAX  ; Store j to register R8 (32-bit)
    JMP WHILE_331
END_WHILE_331:
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13
    POP R12
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_reverse_array) < 1024
times 1024 - ($ - FUNC_reverse_array) db 0x90
%endif

FUNC_count_matching:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 24  ; Allocate stack for all locals
    MOV RAX, 0
    MOV R9D, EAX  ; Initialize count in register R9 (32-bit)
    MOV RAX, 0
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
FOR_401:
    MOV R10, RBX  ; Use i from register
    MOV RAX, RSI  ; Load parameter len
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ END_FOR_401
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter arr
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV RAX, RDX  ; Load parameter value
    CMP RAX, R10
    SETE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_411
    MOV EAX, R9D  ; Load count from register R9 (32-bit)
    ADD RAX, 1
    MOV R9D, EAX  ; Store count to register R9 (32-bit)
    JMP END_IF_411
ELSE_411:
END_IF_411:
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    ADD RAX, 1
    MOV EBX, EAX  ; Store i to register RBX (32-bit)
    JMP FOR_401
END_FOR_401:
    MOV EAX, R9D  ; Load count from register R9 (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_count_matching) < 1024
times 1024 - ($ - FUNC_count_matching) db 0x90
%endif

FUNC_init_array:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 8  ; Allocate stack for all locals
    MOV RAX, 0
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
FOR_449:
    MOV R10, RBX  ; Use i from register
    MOV RAX, RSI  ; Load parameter len
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ END_FOR_449
    MOV RAX, RDX  ; Load parameter start_value
    MOV R10, RAX  ; Save left operand
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    ADD RAX, R10
    PUSH RAX  ; Save value to assign
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    PUSH RAX  ; Save index
    MOV RBX, RDI  ; Base from parameter arr
    POP RAX  ; Get index
    ; Array assignment: base + index * 4
    LEA RAX, [RBX + RAX*4]  ; base + index*4
    POP RCX  ; Get value to assign
    MOV DWORD [RAX], ECX  ; Store to array element
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    ADD RAX, 1
    MOV EBX, EAX  ; Store i to register RBX (32-bit)
    JMP FOR_449
END_FOR_449:
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13
    POP R12
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_init_array) < 1024
times 1024 - ($ - FUNC_init_array) db 0x90
%endif

FUNC_test_array_modulo:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 24  ; Allocate stack for all locals
    MOV RAX, 0
    MOV R9D, EAX  ; Initialize sum in register R9 (32-bit)
    MOV RAX, 0
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
FOR_510:
    MOV R10, RBX  ; Use i from register
    MOV RAX, RSI  ; Load parameter len
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ END_FOR_510
    MOV R10, RBX  ; Use i from register
    MOV RAX, RSI  ; Load parameter len
    ; Modulo operation: R10 % RAX
    PUSH RAX  ; Save right operand (divisor)
    MOV RAX, R10  ; Move left operand (dividend) to RAX
    POP R10  ; Get divisor
    XOR RDX, RDX  ; Clear RDX for division
    DIV R10  ; RAX = dividend / divisor, RDX = remainder
    MOV RAX, RDX  ; Remainder is the modulo result
    MOV DWORD [RBP - 24], EAX  ; Store index (32-bit)
    MOV R10, R9  ; Use sum from register
    MOV EAX, DWORD [RBP - 24]  ; Load index (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter arr
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    ADD RAX, R10
    MOV R9D, EAX  ; Store sum to register R9 (32-bit)
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    ADD RAX, 1
    MOV EBX, EAX  ; Store i to register RBX (32-bit)
    JMP FOR_510
END_FOR_510:
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
%if ($ - FUNC_test_array_modulo) < 1024
times 1024 - ($ - FUNC_test_array_modulo) db 0x90
%endif

FUNC_test_array_comparisons:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 24  ; Allocate stack for all locals
    MOV RAX, 0
    MOV R9D, EAX  ; Initialize count in register R9 (32-bit)
    MOV RAX, 0
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
FOR_569:
    MOV R10, RBX  ; Use i from register
    MOV RAX, RSI  ; Load parameter len
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ END_FOR_569
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter arr
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV RAX, 10
    CMP RAX, R10
    SETG AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_579
    MOV EAX, R9D  ; Load count from register R9 (32-bit)
    ADD RAX, 1
    MOV R9D, EAX  ; Store count to register R9 (32-bit)
    JMP END_IF_579
ELSE_579:
END_IF_579:
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter arr
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV RAX, 20
    CMP RAX, R10
    SETGE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_597
    MOV EAX, R9D  ; Load count from register R9 (32-bit)
    ADD RAX, 1
    MOV R9D, EAX  ; Store count to register R9 (32-bit)
    JMP END_IF_597
ELSE_597:
END_IF_597:
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter arr
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV RAX, 5
    CMP R10, RAX
    SETLE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_615
    MOV EAX, R9D  ; Load count from register R9 (32-bit)
    ADD RAX, 1
    MOV R9D, EAX  ; Store count to register R9 (32-bit)
    JMP END_IF_615
ELSE_615:
END_IF_615:
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter arr
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV RAX, 0
    CMP RAX, R10
    SETNE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_633
    MOV EAX, R9D  ; Load count from register R9 (32-bit)
    ADD RAX, 1
    MOV R9D, EAX  ; Store count to register R9 (32-bit)
    JMP END_IF_633
ELSE_633:
END_IF_633:
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    ADD RAX, 1
    MOV EBX, EAX  ; Store i to register RBX (32-bit)
    JMP FOR_569
END_FOR_569:
    MOV EAX, R9D  ; Load count from register R9 (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_array_comparisons) < 1024
times 1024 - ($ - FUNC_test_array_comparisons) db 0x90
%endif

FUNC_test_array_logical:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 24  ; Allocate stack for all locals
    MOV RAX, 0
    MOV R9D, EAX  ; Initialize count in register R9 (32-bit)
    MOV RAX, 0
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
FOR_682:
    MOV R10, RBX  ; Use i from register
    MOV RAX, RSI  ; Load parameter len
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ END_FOR_682
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter arr
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV RAX, 0
    CMP RAX, R10
    SETG AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_692
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter arr
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV RAX, 100
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_692
    MOV EAX, R9D  ; Load count from register R9 (32-bit)
    ADD RAX, 1
    MOV R9D, EAX  ; Store count to register R9 (32-bit)
    JMP END_IF_692
ELSE_692:
END_IF_692:
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter arr
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV RAX, 0
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    MOV R10, RAX  ; Save left operand
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter arr
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV RAX, 1000
    CMP RAX, R10
    SETG AL
    MOVZX RAX, AL
    ; Logical OR: R10 || RAX
    TEST R10, R10  ; Check if left is non-zero
    JNZ OR_TRUE_1
    TEST RAX, RAX  ; Check if right is non-zero
    JNZ OR_TRUE_1
    MOV RAX, 0  ; Both zero, result is 0
    JMP OR_END_1
OR_TRUE_1:
    MOV RAX, 1  ; At least one non-zero, result is 1
OR_END_1:
    TEST RAX, RAX
    JZ ELSE_722
    MOV EAX, R9D  ; Load count from register R9 (32-bit)
    ADD RAX, 1
    MOV R9D, EAX  ; Store count to register R9 (32-bit)
    JMP END_IF_722
ELSE_722:
END_IF_722:
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    ADD RAX, 1
    MOV EBX, EAX  ; Store i to register RBX (32-bit)
    JMP FOR_682
END_FOR_682:
    MOV EAX, R9D  ; Load count from register R9 (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_array_logical) < 1024
times 1024 - ($ - FUNC_test_array_logical) db 0x90
%endif

FUNC_left_shift:
    MOV RAX, RDI  ; Load parameter value
    MOV R10, RAX  ; Save left operand
    MOV RAX, RSI  ; Load parameter shift
    ; Left shift: R10 << RAX
    MOV RCX, RAX  ; Shift amount in RCX
    MOV RAX, R10  ; Value to shift
    SHL RAX, CL  ; Left shift by CL (low 8 bits of RCX)
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_left_shift) < 1024
times 1024 - ($ - FUNC_left_shift) db 0x90
%endif

FUNC_right_shift:
    MOV RAX, RDI  ; Load parameter value
    MOV R10, RAX  ; Save left operand
    MOV RAX, RSI  ; Load parameter shift
    ; Right shift: R10 >> RAX
    MOV RCX, RAX  ; Shift amount in RCX
    MOV RAX, R10  ; Value to shift
    SHR RAX, CL  ; Right shift by CL (low 8 bits of RCX)
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_right_shift) < 1024
times 1024 - ($ - FUNC_right_shift) db 0x90
%endif

FUNC_bitwise_and:
    MOV RAX, RDI  ; Load parameter a
    MOV R10, RAX  ; Save left operand
    MOV RAX, RSI  ; Load parameter b
    ; Bitwise AND: R10 & RAX
    AND RAX, R10
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_bitwise_and) < 1024
times 1024 - ($ - FUNC_bitwise_and) db 0x90
%endif

FUNC_bitwise_or:
    MOV RAX, RDI  ; Load parameter a
    MOV R10, RAX  ; Save left operand
    MOV RAX, RSI  ; Load parameter b
    ; Bitwise OR: R10 | RAX
    OR RAX, R10
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_bitwise_or) < 1024
times 1024 - ($ - FUNC_bitwise_or) db 0x90
%endif

FUNC_bitwise_xor:
    MOV RAX, RDI  ; Load parameter a
    MOV R10, RAX  ; Save left operand
    MOV RAX, RSI  ; Load parameter b
    ; Bitwise XOR: R10 ^ RAX
    XOR RAX, R10
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_bitwise_xor) < 1024
times 1024 - ($ - FUNC_bitwise_xor) db 0x90
%endif

FUNC_bitwise_not:
    MOV RAX, RDI  ; Load parameter a
    ; Bitwise NOT: ~expr
    NOT RAX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_bitwise_not) < 1024
times 1024 - ($ - FUNC_bitwise_not) db 0x90
%endif

FUNC_bitwise_combined:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 8  ; Allocate stack for all locals
    MOV R10, RDI  ; Use a from register
    MOV RAX, 2
    ; Left shift: R10 << RAX
    MOV RCX, RAX  ; Shift amount in RCX
    MOV RAX, R10  ; Value to shift
    SHL RAX, CL  ; Left shift by CL (low 8 bits of RCX)
    MOV R10, RAX  ; Save left operand
    MOV RAX, RSI  ; Load parameter b
    MOV R10, RAX  ; Save left operand
    MOV RAX, 1
    ; Right shift: R10 >> RAX
    MOV RCX, RAX  ; Shift amount in RCX
    MOV RAX, R10  ; Value to shift
    SHR RAX, CL  ; Right shift by CL (low 8 bits of RCX)
    ; Bitwise AND: R10 & RAX
    AND RAX, R10
    MOV EBX, EAX  ; Initialize result in register RBX (32-bit)
    MOV R10, RBX  ; Use result from register
    MOV RAX, RDX  ; Load parameter c
    MOV R10, RAX  ; Save left operand
    MOV RAX, 255
    ; Bitwise AND: R10 & RAX
    AND RAX, R10
    ; Bitwise OR: R10 | RAX
    OR RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV R10, RBX  ; Use result from register
    MOV R10, RDI  ; Use a from register
    MOV RAX, 1
    ; Left shift: R10 << RAX
    MOV RCX, RAX  ; Shift amount in RCX
    MOV RAX, R10  ; Value to shift
    SHL RAX, CL  ; Left shift by CL (low 8 bits of RCX)
    ; Bitwise XOR: R10 ^ RAX
    XOR RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    ; Bitwise NOT: ~expr
    NOT RAX
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_bitwise_combined) < 1024
times 1024 - ($ - FUNC_bitwise_combined) db 0x90
%endif

FUNC_power_of_2:
    MOV R10, RDI  ; Use n from register
    MOV RAX, 0
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_917
    MOV RAX, 0
    RET
    JMP END_IF_917
ELSE_917:
END_IF_917:
    MOV RAX, 1
    MOV R10, RAX  ; Save left operand
    MOV RAX, RDI  ; Load parameter n
    ; Left shift: R10 << RAX
    MOV RCX, RAX  ; Shift amount in RCX
    MOV RAX, R10  ; Value to shift
    SHL RAX, CL  ; Left shift by CL (low 8 bits of RCX)
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_power_of_2) < 1024
times 1024 - ($ - FUNC_power_of_2) db 0x90
%endif

FUNC_extract_bits:
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 8  ; Allocate stack for all locals
    MOV RAX, 1
    MOV R10, RAX  ; Save left operand
    MOV RAX, RDX  ; Load parameter count
    ; Left shift: R10 << RAX
    MOV RCX, RAX  ; Shift amount in RCX
    MOV RAX, R10  ; Value to shift
    SHL RAX, CL  ; Left shift by CL (low 8 bits of RCX)
    SUB RAX, 1
    MOV R10, RAX  ; Save left operand
    MOV RAX, RSI  ; Load parameter start
    ; Left shift: R10 << RAX
    MOV RCX, RAX  ; Shift amount in RCX
    MOV RAX, R10  ; Value to shift
    SHL RAX, CL  ; Left shift by CL (low 8 bits of RCX)
    MOV DWORD [RBP - 8], EAX  ; Store mask (32-bit)
    MOV RAX, RDI  ; Load parameter value
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 8]  ; Load mask (32-bit)
    ; Bitwise AND: R10 & RAX
    AND RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV RAX, RSI  ; Load parameter start
    ; Right shift: R10 >> RAX
    MOV RCX, RAX  ; Shift amount in RCX
    MOV RAX, R10  ; Value to shift
    SHR RAX, CL  ; Right shift by CL (low 8 bits of RCX)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_extract_bits) < 1024
times 1024 - ($ - FUNC_extract_bits) db 0x90
%endif

FUNC_set_bits:
    MOV RAX, RDI  ; Load parameter value
    MOV R10, RAX  ; Save left operand
    MOV RAX, RSI  ; Load parameter bits
    ; Bitwise OR: R10 | RAX
    OR RAX, R10
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_set_bits) < 1024
times 1024 - ($ - FUNC_set_bits) db 0x90
%endif

FUNC_clear_bits:
    MOV RAX, RDI  ; Load parameter value
    MOV R10, RAX  ; Save left operand
    MOV RAX, RSI  ; Load parameter bits
    ; Bitwise NOT: ~expr
    NOT RAX
    ; Bitwise AND: R10 & RAX
    AND RAX, R10
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_clear_bits) < 1024
times 1024 - ($ - FUNC_clear_bits) db 0x90
%endif

FUNC_toggle_bits:
    MOV RAX, RDI  ; Load parameter value
    MOV R10, RAX  ; Save left operand
    MOV RAX, RSI  ; Load parameter bits
    ; Bitwise XOR: R10 ^ RAX
    XOR RAX, R10
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_toggle_bits) < 1024
times 1024 - ($ - FUNC_toggle_bits) db 0x90
%endif

FUNC_test_compound_bitwise:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 8  ; Allocate stack for all locals
    MOV RAX, RDI  ; Load parameter a
    MOV EBX, EAX  ; Initialize result in register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    PUSH RAX  ; Save current value
    MOV RAX, 2
    POP R10  ; Get current value
    MOV RCX, RAX  ; Shift amount
    MOV RAX, R10  ; Value to shift
    SHL RAX, CL
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    PUSH RAX  ; Save current value
    MOV RAX, 1
    POP R10  ; Get current value
    MOV RCX, RAX  ; Shift amount
    MOV RAX, R10  ; Value to shift
    SHR RAX, CL
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    PUSH RAX  ; Save current value
    MOV RAX, RSI  ; Load parameter b
    POP R10  ; Get current value
    AND RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    PUSH RAX  ; Save current value
    MOV RAX, RDI  ; Load parameter a
    POP R10  ; Get current value
    OR RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    PUSH RAX  ; Save current value
    MOV RAX, RSI  ; Load parameter b
    POP R10  ; Get current value
    XOR RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_compound_bitwise) < 1024
times 1024 - ($ - FUNC_test_compound_bitwise) db 0x90
%endif

FUNC_factorial:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 24  ; Allocate stack for all locals
    MOV RAX, 1
    MOV R9D, EAX  ; Initialize result in register R9 (32-bit)
    MOV RAX, 1
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
WHILE_1101:
    MOV R10, RBX  ; Use i from register
    MOV RAX, RDI  ; Load parameter n
    CMP R10, RAX
    SETLE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ END_WHILE_1101
    MOV R10, R9  ; Use result from register
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MUL R10
    MOV R9D, EAX  ; Store result to register R9 (32-bit)
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    ADD RAX, 1
    MOV EBX, EAX  ; Store i to register RBX (32-bit)
    JMP WHILE_1101
END_WHILE_1101:
    MOV EAX, R9D  ; Load result from register R9 (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_factorial) < 1024
times 1024 - ($ - FUNC_factorial) db 0x90
%endif

FUNC_fibonacci:
    MOV R10, RDI  ; Use n from register
    MOV RAX, 0
    CMP R10, RAX
    SETLE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_1133
    MOV RAX, 0
    POP RBX  ; Restore callee-saved RBX
    RET
    JMP END_IF_1133
ELSE_1133:
END_IF_1133:
    MOV R10, RDI  ; Use n from register
    MOV RAX, 1
    CMP RAX, R10
    SETE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_1146
    MOV RAX, 1
    POP RBX  ; Restore callee-saved RBX
    RET
    JMP END_IF_1146
ELSE_1146:
END_IF_1146:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 40  ; Allocate stack for all locals
    MOV RAX, 0
    MOV DWORD [RBP - 8], EAX  ; Store a (32-bit)
    MOV RAX, 1
    MOV R9D, EAX  ; Initialize b in register R9 (32-bit)
    MOV RAX, 0
    MOV DWORD [RBP - 24], EAX  ; Store temp (32-bit)
    MOV RAX, 2
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
FOR_1174:
    MOV R10, RBX  ; Use i from register
    MOV RAX, RDI  ; Load parameter n
    CMP R10, RAX
    SETLE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ END_FOR_1174
    MOV EAX, DWORD [RBP - 8]  ; Load a (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV EAX, R9D  ; Load b from register R9 (32-bit)
    ADD RAX, R10
    MOV DWORD [RBP - 24], EAX  ; Store temp (32-bit)
    MOV EAX, R9D  ; Load b from register R9 (32-bit)
    MOV [GLOBAL_a], RAX
    MOV EAX, DWORD [RBP - 24]  ; Load temp (32-bit)
    MOV [GLOBAL_b], RAX
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    ADD RAX, 1
    MOV EBX, EAX  ; Store i to register RBX (32-bit)
    JMP FOR_1174
END_FOR_1174:
    MOV EAX, R9D  ; Load b from register R9 (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_fibonacci) < 1024
times 1024 - ($ - FUNC_fibonacci) db 0x90
%endif

FUNC_sum_array:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 24  ; Allocate stack for all locals
    MOV RAX, 0
    MOV R9D, EAX  ; Initialize sum in register R9 (32-bit)
    MOV RAX, 0
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
WHILE_1226:
    MOV R10, RBX  ; Use i from register
    MOV RAX, RSI  ; Load parameter len
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ END_WHILE_1226
    MOV R10, R9  ; Use sum from register
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter arr
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    ADD RAX, R10
    MOV R9D, EAX  ; Store sum to register R9 (32-bit)
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    ADD RAX, 1
    MOV EBX, EAX  ; Store i to register RBX (32-bit)
    JMP WHILE_1226
END_WHILE_1226:
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
%if ($ - FUNC_sum_array) < 1024
times 1024 - ($ - FUNC_sum_array) db 0x90
%endif

FUNC_count_even:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 24  ; Allocate stack for all locals
    MOV RAX, 0
    MOV R9D, EAX  ; Initialize count in register R9 (32-bit)
    MOV RAX, 0
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
FOR_1273:
    MOV R10, RBX  ; Use i from register
    MOV RAX, RSI  ; Load parameter len
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ END_FOR_1273
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter arr
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV RAX, 2
    ; Modulo operation: R10 % RAX
    PUSH RAX  ; Save right operand (divisor)
    MOV RAX, R10  ; Move left operand (dividend) to RAX
    POP R10  ; Get divisor
    XOR RDX, RDX  ; Clear RDX for division
    DIV R10  ; RAX = dividend / divisor, RDX = remainder
    MOV RAX, RDX  ; Remainder is the modulo result
    MOV R10, RAX  ; Save left operand
    MOV RAX, 0
    CMP RAX, R10
    SETE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_1283
    MOV EAX, R9D  ; Load count from register R9 (32-bit)
    ADD RAX, 1
    MOV R9D, EAX  ; Store count to register R9 (32-bit)
    JMP END_IF_1283
ELSE_1283:
END_IF_1283:
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    ADD RAX, 1
    MOV EBX, EAX  ; Store i to register RBX (32-bit)
    JMP FOR_1273
END_FOR_1273:
    MOV EAX, R9D  ; Load count from register R9 (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_count_even) < 1024
times 1024 - ($ - FUNC_count_even) db 0x90
%endif

FUNC_classify_number:
    MOV R10, RDI  ; Use n from register
    MOV RAX, 0
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_1330
    MOV RAX, 1
    NEG RAX
    RET
    JMP END_IF_1330
ELSE_1330:
    MOV R10, RDI  ; Use n from register
    MOV RAX, 0
    CMP RAX, R10
    SETE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_1342
    MOV RAX, 0
    RET
    JMP END_IF_1342
ELSE_1342:
    MOV R10, RDI  ; Use n from register
    MOV RAX, 10
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_1353
    MOV RAX, 1
    RET
    JMP END_IF_1353
ELSE_1353:
    MOV R10, RDI  ; Use n from register
    MOV RAX, 100
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_1364
    MOV RAX, 2
    RET
    JMP END_IF_1364
ELSE_1364:
    MOV RAX, 3
    RET
END_IF_1364:
END_IF_1353:
END_IF_1342:
END_IF_1330:
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_classify_number) < 1024
times 1024 - ($ - FUNC_classify_number) db 0x90
%endif

FUNC_matrix_sum:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 40  ; Allocate stack for all locals
    MOV RAX, 0
    MOV R10D, EAX  ; Initialize sum in register R10 (32-bit)
    MOV RAX, 0
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
FOR_1399:
    PUSH R10  ; Save sum
    MOV R10, RBX  ; Use i from register
    MOV RAX, RDI  ; Load parameter size
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    POP R10  ; Restore temp
    TEST RAX, RAX
    JZ END_FOR_1399
    MOV RAX, 0
    MOV R8D, EAX  ; Initialize j in register R8 (32-bit)
FOR_1411:
    PUSH R10  ; Save sum
    MOV R10, R8  ; Use j from register
    MOV RAX, RDI  ; Load parameter size
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    POP R10  ; Restore temp
    TEST RAX, RAX
    JZ END_FOR_1411
    PUSH R10  ; Save sum
    MOV R10, RBX  ; Use i from register
    MOV RAX, RDI  ; Load parameter size
    MUL R10
    POP R10  ; Restore temp
    PUSH R10  ; Save sum
    MOV R10, RAX  ; Save left operand
    MOV EAX, R8D  ; Load j from register R8 (32-bit)
    ADD RAX, R10
    POP R10  ; Restore temp
    MOV DWORD [RBP - 32], EAX  ; Store index (32-bit)
    MOV R10, R10  ; Use sum from register
    MOV EAX, DWORD [RBP - 32]  ; Load index (32-bit)
    ADD RAX, R10
    MOV R10D, EAX  ; Store sum to register R10 (32-bit)
    MOV EAX, R8D  ; Load j from register R8 (32-bit)
    ADD RAX, 1
    MOV R8D, EAX  ; Store j to register R8 (32-bit)
    JMP FOR_1411
END_FOR_1411:
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    ADD RAX, 1
    MOV EBX, EAX  ; Store i to register RBX (32-bit)
    JMP FOR_1399
END_FOR_1399:
    MOV EAX, R10D  ; Load sum from register R10 (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_matrix_sum) < 1024
times 1024 - ($ - FUNC_matrix_sum) db 0x90
%endif

FUNC_find_value:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 8  ; Allocate stack for all locals
    MOV RAX, 0
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
FOR_1463:
    MOV R10, RBX  ; Use i from register
    MOV RAX, RSI  ; Load parameter len
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ END_FOR_1463
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter arr
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV RAX, RDX  ; Load parameter target
    CMP RAX, R10
    SETE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_1482
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    JMP END_IF_1482
ELSE_1482:
END_IF_1482:
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    ADD RAX, 1
    MOV EBX, EAX  ; Store i to register RBX (32-bit)
    JMP FOR_1463
END_FOR_1463:
    MOV RAX, 1
    NEG RAX
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_find_value) < 1024
times 1024 - ($ - FUNC_find_value) db 0x90
%endif

FUNC_sum_until_negative:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 24  ; Allocate stack for all locals
    MOV RAX, 0
    MOV R9D, EAX  ; Initialize sum in register R9 (32-bit)
    MOV RAX, 0
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
WHILE_1540:
    MOV R10, RBX  ; Use i from register
    MOV RAX, RSI  ; Load parameter len
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ END_WHILE_1540
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter arr
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV RAX, 0
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_1548
    MOV EAX, R9D  ; Load sum from register R9 (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    JMP END_IF_1548
ELSE_1548:
END_IF_1548:
    MOV R10, R9  ; Use sum from register
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter arr
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    ADD RAX, R10
    MOV R9D, EAX  ; Store sum to register R9 (32-bit)
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    ADD RAX, 1
    MOV EBX, EAX  ; Store i to register RBX (32-bit)
    JMP WHILE_1540
END_WHILE_1540:
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
%if ($ - FUNC_sum_until_negative) < 1024
times 1024 - ($ - FUNC_sum_until_negative) db 0x90
%endif

FUNC_process_data:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 24  ; Allocate stack for all locals
    MOV RAX, 0
    MOV R9D, EAX  ; Initialize processed in register R9 (32-bit)
    MOV RAX, 0
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
FOR_1611:
    MOV R10, RBX  ; Use i from register
    MOV RAX, RSI  ; Load parameter len
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ END_FOR_1611
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter data
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV RAX, 0
    CMP RAX, R10
    SETG AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_1621
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter data
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    ADD RAX, RAX
    PUSH RAX  ; Save value to assign
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    PUSH RAX  ; Save index
    MOV RBX, RDI  ; Base from parameter data
    POP RAX  ; Get index
    ; Array assignment: base + index * 4
    LEA RAX, [RBX + RAX*4]  ; base + index*4
    POP RCX  ; Get value to assign
    MOV DWORD [RAX], ECX  ; Store to array element
    MOV EAX, R9D  ; Load processed from register R9 (32-bit)
    ADD RAX, 1
    MOV R9D, EAX  ; Store processed to register R9 (32-bit)
    JMP END_IF_1621
ELSE_1621:
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter data
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV RAX, 0
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_1653
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    MOV RAX, RDI  ; Base from parameter data
    LEA RAX, [RAX + RCX*4]  ; Base + index*4
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    NEG RAX
    PUSH RAX  ; Save value to assign
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    PUSH RAX  ; Save index
    MOV RBX, RDI  ; Base from parameter data
    POP RAX  ; Get index
    ; Array assignment: base + index * 4
    LEA RAX, [RBX + RAX*4]  ; base + index*4
    POP RCX  ; Get value to assign
    MOV DWORD [RAX], ECX  ; Store to array element
    MOV EAX, R9D  ; Load processed from register R9 (32-bit)
    ADD RAX, 1
    MOV R9D, EAX  ; Store processed to register R9 (32-bit)
    JMP END_IF_1653
ELSE_1653:
END_IF_1653:
END_IF_1621:
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    ADD RAX, 1
    MOV EBX, EAX  ; Store i to register RBX (32-bit)
    JMP FOR_1611
END_FOR_1611:
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13
    POP R12
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_process_data) < 1024
times 1024 - ($ - FUNC_process_data) db 0x90
%endif

FUNC_test_globals:
    MOV RAX, [GLOBAL_global_counter]  ; Load global variable
    ADD RAX, 1
    MOV [GLOBAL_global_counter], RAX
    MOV R10, R8  ; Use global_sum from register
    MOV RAX, [GLOBAL_global_counter]  ; Load global variable
    ADD RAX, R10
    MOV [GLOBAL_global_sum], RAX
    MOV R10, RBX  ; Use global_counter from register
    MOV RAX, [GLOBAL_global_max]  ; Load global variable
    CMP RAX, R10
    SETG AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_1712
    MOV RAX, [GLOBAL_global_counter]  ; Load global variable
    MOV [GLOBAL_global_max], RAX
    JMP END_IF_1712
ELSE_1712:
END_IF_1712:
    MOV R10, RBX  ; Use global_counter from register
    MOV RAX, [GLOBAL_global_min]  ; Load global variable
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_1724
    MOV RAX, [GLOBAL_global_counter]  ; Load global variable
    MOV [GLOBAL_global_min], RAX
    JMP END_IF_1724
ELSE_1724:
END_IF_1724:
    MOV RAX, [GLOBAL_global_sum]  ; Load global variable
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_globals) < 1024
times 1024 - ($ - FUNC_test_globals) db 0x90
%endif

FUNC_test_simd_packed:
    MOV RAX, 1
    MOV BYTE [GLOBAL_flag_1bit], AL  ; Store to packed variable
    MOV RAX, 3
    MOV BYTE [GLOBAL_counter_2bit], AL  ; Store to packed variable
    MOV RAX, 5
    MOV BYTE [GLOBAL_state_3bit], AL  ; Store to packed variable
    MOV RAX, 10
    MOV BYTE [GLOBAL_mode_4bit], AL  ; Store to packed variable
    MOV RAX, 15
    MOV BYTE [GLOBAL_level_5bit], AL  ; Store to packed variable
    MOV RAX, 20
    MOV BYTE [GLOBAL_index_6bit], AL  ; Store to packed variable
    MOV RAX, 30
    MOV BYTE [GLOBAL_offset_7bit], AL  ; Store to packed variable
    MOV RAX, 50
    MOV BYTE [GLOBAL_value_8bit], AL  ; Store to packed variable
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 8  ; Allocate stack for all locals
    MOV RAX, 0
    MOV EBX, EAX  ; Initialize result in register RBX (32-bit)
    MOV R10, RBX  ; Use result from register
    MOVZX EAX, BYTE [GLOBAL_flag_1bit]  ; Load packed variable
    ADD RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV R10, RBX  ; Use result from register
    MOVZX EAX, BYTE [GLOBAL_counter_2bit]  ; Load packed variable
    ADD RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV R10, RBX  ; Use result from register
    MOVZX EAX, BYTE [GLOBAL_state_3bit]  ; Load packed variable
    ADD RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV R10, RBX  ; Use result from register
    MOVZX EAX, BYTE [GLOBAL_mode_4bit]  ; Load packed variable
    ADD RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV R10, RBX  ; Use result from register
    MOVZX EAX, BYTE [GLOBAL_level_5bit]  ; Load packed variable
    ADD RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV R10, RBX  ; Use result from register
    MOVZX EAX, BYTE [GLOBAL_index_6bit]  ; Load packed variable
    ADD RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV R10, RBX  ; Use result from register
    MOVZX EAX, BYTE [GLOBAL_offset_7bit]  ; Load packed variable
    ADD RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV R10, RBX  ; Use result from register
    MOVZX EAX, BYTE [GLOBAL_value_8bit]  ; Load packed variable
    ADD RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_simd_packed) < 1024
times 1024 - ($ - FUNC_test_simd_packed) db 0x90
%endif

FUNC_test_mixed_globals:
    MOV RAX, [GLOBAL_global_counter]  ; Load global variable
    ADD RAX, 1
    MOV [GLOBAL_global_counter], RAX
    MOV R10, RBX  ; Use global_counter from register
    MOV RAX, 2
    ; Modulo operation: R10 % RAX
    PUSH RAX  ; Save right operand (divisor)
    MOV RAX, R10  ; Move left operand (dividend) to RAX
    POP R10  ; Get divisor
    XOR RDX, RDX  ; Clear RDX for division
    DIV R10  ; RAX = dividend / divisor, RDX = remainder
    MOV RAX, RDX  ; Remainder is the modulo result
    MOV BYTE [GLOBAL_flag_1bit], AL  ; Store to packed variable
    MOV R10, RBX  ; Use global_counter from register
    MOV RAX, 4
    ; Modulo operation: R10 % RAX
    PUSH RAX  ; Save right operand (divisor)
    MOV RAX, R10  ; Move left operand (dividend) to RAX
    POP R10  ; Get divisor
    XOR RDX, RDX  ; Clear RDX for division
    DIV R10  ; RAX = dividend / divisor, RDX = remainder
    MOV RAX, RDX  ; Remainder is the modulo result
    MOV BYTE [GLOBAL_counter_2bit], AL  ; Store to packed variable
    MOV R10, RBX  ; Use global_counter from register
    MOV RAX, 8
    ; Modulo operation: R10 % RAX
    PUSH RAX  ; Save right operand (divisor)
    MOV RAX, R10  ; Move left operand (dividend) to RAX
    POP R10  ; Get divisor
    XOR RDX, RDX  ; Clear RDX for division
    DIV R10  ; RAX = dividend / divisor, RDX = remainder
    MOV RAX, RDX  ; Remainder is the modulo result
    MOV BYTE [GLOBAL_state_3bit], AL  ; Store to packed variable
    MOV R10, RBX  ; Use global_counter from register
    MOVZX EAX, BYTE [GLOBAL_flag_1bit]  ; Load packed variable
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOVZX EAX, BYTE [GLOBAL_counter_2bit]  ; Load packed variable
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOVZX EAX, BYTE [GLOBAL_state_3bit]  ; Load packed variable
    ADD RAX, R10
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_mixed_globals) < 1024
times 1024 - ($ - FUNC_test_mixed_globals) db 0x90
%endif

FUNC_isr_timer_handler:
    ; Interrupt callback: using zero-latency SIMD register access
    ; xmm15 contains packed kernel flags (no memory reads)
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 8  ; Allocate stack space for SIMD register
    SUB RSP, 24  ; Allocate stack for all locals
    ; Zero-latency read from packed variable flag_1bit
    MOVQ RAX, xmm15  ; Load packed register
    SHR RAX, 42  ; Shift to extract flag_1bit
    AND RAX, 1  ; Mask to 1 bits
    MOV DWORD [RBP - 8], EAX  ; Store current_flag (32-bit)
    ; Zero-latency read from packed variable counter_2bit
    MOVQ RAX, xmm15  ; Load packed register
    SHR RAX, 43  ; Shift to extract counter_2bit
    AND RAX, 3  ; Mask to 2 bits
    MOV DWORD [RBP - 16], EAX  ; Store current_counter (32-bit)
    ; Zero-latency read from packed variable state_3bit
    MOVQ RAX, xmm15  ; Load packed register
    SHR RAX, 45  ; Shift to extract state_3bit
    AND RAX, 7  ; Mask to 3 bits
    MOV DWORD [RBP - 24], EAX  ; Store current_state (32-bit)
    MOV EAX, DWORD [RBP - 8]  ; Load current_flag (32-bit)
    NOT RAX
    ; Zero-latency write to packed variable flag_1bit
    PUSH RAX  ; Save value to write
    MOVQ RAX, xmm15  ; Load packed register
    MOV R10, 4398046511104
    NOT R10  ; Invert mask
    AND RAX, R10  ; Clear bits for flag_1bit
    POP R10  ; Restore value to write
    AND R10, 1  ; Mask to 1 bits
    SHL R10, 42  ; Shift to position
    OR RAX, R10  ; Insert new value
    MOVQ xmm15, RAX  ; Store back to SIMD register
    MOV EAX, DWORD [RBP - 16]  ; Load current_counter (32-bit)
    ADD RAX, 1
    MOV R10, RAX  ; Save left operand
    MOV RAX, 4
    ; Modulo operation: R10 % RAX
    PUSH RAX  ; Save right operand (divisor)
    MOV RAX, R10  ; Move left operand (dividend) to RAX
    POP R10  ; Get divisor
    XOR RDX, RDX  ; Clear RDX for division
    DIV R10  ; RAX = dividend / divisor, RDX = remainder
    MOV RAX, RDX  ; Remainder is the modulo result
    ; Zero-latency write to packed variable counter_2bit
    PUSH RAX  ; Save value to write
    MOVQ RAX, xmm15  ; Load packed register
    MOV R10, 26388279066624
    NOT R10  ; Invert mask
    AND RAX, R10  ; Clear bits for counter_2bit
    POP R10  ; Restore value to write
    AND R10, 3  ; Mask to 2 bits
    SHL R10, 43  ; Shift to position
    OR RAX, R10  ; Insert new value
    MOVQ xmm15, RAX  ; Store back to SIMD register
    MOV EAX, DWORD [RBP - 24]  ; Load current_state (32-bit)
    ADD RAX, 1
    MOV R10, RAX  ; Save left operand
    MOV RAX, 8
    ; Modulo operation: R10 % RAX
    PUSH RAX  ; Save right operand (divisor)
    MOV RAX, R10  ; Move left operand (dividend) to RAX
    POP R10  ; Get divisor
    XOR RDX, RDX  ; Clear RDX for division
    DIV R10  ; RAX = dividend / divisor, RDX = remainder
    MOV RAX, RDX  ; Remainder is the modulo result
    ; Zero-latency write to packed variable state_3bit
    PUSH RAX  ; Save value to write
    MOVQ RAX, xmm15  ; Load packed register
    MOV R10, 246290604621824
    NOT R10  ; Invert mask
    AND RAX, R10  ; Clear bits for state_3bit
    POP R10  ; Restore value to write
    AND R10, 7  ; Mask to 3 bits
    SHL R10, 45  ; Shift to position
    OR RAX, R10  ; Insert new value
    MOVQ xmm15, RAX  ; Store back to SIMD register
    MOV EAX, DWORD [RBP - 8]  ; Load current_flag (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 16]  ; Load current_counter (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 24]  ; Load current_state (32-bit)
    ADD RAX, R10
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_isr_timer_handler) < 1024
times 1024 - ($ - FUNC_isr_timer_handler) db 0x90
%endif

FUNC_irq_keyboard_handler:
    ; Interrupt callback: using zero-latency SIMD register access
    ; xmm15 contains packed kernel flags (no memory reads)
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 8  ; Allocate stack space for SIMD register
    SUB RSP, 24  ; Allocate stack for all locals
    ; Zero-latency read from packed variable flag_1bit
    MOVQ RAX, xmm15  ; Load packed register
    SHR RAX, 42  ; Shift to extract flag_1bit
    AND RAX, 1  ; Mask to 1 bits
    MOV DWORD [RBP - 8], EAX  ; Store flag (32-bit)
    ; Zero-latency read from packed variable counter_2bit
    MOVQ RAX, xmm15  ; Load packed register
    SHR RAX, 43  ; Shift to extract counter_2bit
    AND RAX, 3  ; Mask to 2 bits
    MOV DWORD [RBP - 16], EAX  ; Store counter (32-bit)
    MOV EAX, DWORD [RBP - 8]  ; Load flag (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV RAX, 1
    CMP RAX, R10
    SETE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_1993
    ; Zero-latency read from packed variable state_3bit
    MOVQ RAX, xmm15  ; Load packed register
    SHR RAX, 45  ; Shift to extract state_3bit
    AND RAX, 7  ; Mask to 3 bits
    ADD RAX, 1
    MOV R10, RAX  ; Save left operand
    MOV RAX, 8
    ; Modulo operation: R10 % RAX
    PUSH RAX  ; Save right operand (divisor)
    MOV RAX, R10  ; Move left operand (dividend) to RAX
    POP R10  ; Get divisor
    XOR RDX, RDX  ; Clear RDX for division
    DIV R10  ; RAX = dividend / divisor, RDX = remainder
    MOV RAX, RDX  ; Remainder is the modulo result
    ; Zero-latency write to packed variable state_3bit
    PUSH RAX  ; Save value to write
    MOVQ RAX, xmm15  ; Load packed register
    MOV R10, 246290604621824
    NOT R10  ; Invert mask
    AND RAX, R10  ; Clear bits for state_3bit
    POP R10  ; Restore value to write
    AND R10, 7  ; Mask to 3 bits
    SHL R10, 45  ; Shift to position
    OR RAX, R10  ; Insert new value
    MOVQ xmm15, RAX  ; Store back to SIMD register
    JMP END_IF_1993
ELSE_1993:
    MOV RAX, 0
    ; Zero-latency write to packed variable state_3bit
    PUSH RAX  ; Save value to write
    MOVQ RAX, xmm15  ; Load packed register
    MOV R10, 246290604621824
    NOT R10  ; Invert mask
    AND RAX, R10  ; Clear bits for state_3bit
    POP R10  ; Restore value to write
    AND R10, 7  ; Mask to 3 bits
    SHL R10, 45  ; Shift to position
    OR RAX, R10  ; Insert new value
    MOVQ xmm15, RAX  ; Store back to SIMD register
END_IF_1993:
    MOV EAX, DWORD [RBP - 16]  ; Load counter (32-bit)
    ADD RAX, 1
    MOV R10, RAX  ; Save left operand
    MOV RAX, 4
    ; Modulo operation: R10 % RAX
    PUSH RAX  ; Save right operand (divisor)
    MOV RAX, R10  ; Move left operand (dividend) to RAX
    POP R10  ; Get divisor
    XOR RDX, RDX  ; Clear RDX for division
    DIV R10  ; RAX = dividend / divisor, RDX = remainder
    MOV RAX, RDX  ; Remainder is the modulo result
    ; Zero-latency write to packed variable counter_2bit
    PUSH RAX  ; Save value to write
    MOVQ RAX, xmm15  ; Load packed register
    MOV R10, 26388279066624
    NOT R10  ; Invert mask
    AND RAX, R10  ; Clear bits for counter_2bit
    POP R10  ; Restore value to write
    AND R10, 3  ; Mask to 2 bits
    SHL R10, 43  ; Shift to position
    OR RAX, R10  ; Insert new value
    MOVQ xmm15, RAX  ; Store back to SIMD register
    MOV EAX, DWORD [RBP - 8]  ; Load flag (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 16]  ; Load counter (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    ; Zero-latency read from packed variable state_3bit
    MOVQ RAX, xmm15  ; Load packed register
    SHR RAX, 45  ; Shift to extract state_3bit
    AND RAX, 7  ; Mask to 3 bits
    ADD RAX, R10
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_irq_keyboard_handler) < 1024
times 1024 - ($ - FUNC_irq_keyboard_handler) db 0x90
%endif

FUNC_generic_interrupt_handler:
    ; Interrupt callback: using zero-latency SIMD register access
    ; xmm15 contains packed kernel flags (no memory reads)
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 8  ; Allocate stack space for SIMD register
    SUB RSP, 8  ; Allocate stack for all locals
    ; Zero-latency read from packed variable flag_1bit
    MOVQ RAX, xmm15  ; Load packed register
    SHR RAX, 42  ; Shift to extract flag_1bit
    AND RAX, 1  ; Mask to 1 bits
    MOV EBX, EAX  ; Initialize result in register RBX (32-bit)
    MOV R10, RBX  ; Use result from register
    ; Zero-latency read from packed variable counter_2bit
    MOVQ RAX, xmm15  ; Load packed register
    SHR RAX, 43  ; Shift to extract counter_2bit
    AND RAX, 3  ; Mask to 2 bits
    ADD RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV R10, RBX  ; Use result from register
    ; Zero-latency read from packed variable state_3bit
    MOVQ RAX, xmm15  ; Load packed register
    SHR RAX, 45  ; Shift to extract state_3bit
    AND RAX, 7  ; Mask to 3 bits
    ADD RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV RAX, 1
    ; Zero-latency write to packed variable flag_1bit
    PUSH RAX  ; Save value to write
    MOVQ RAX, xmm15  ; Load packed register
    MOV R10, 4398046511104
    NOT R10  ; Invert mask
    AND RAX, R10  ; Clear bits for flag_1bit
    POP R10  ; Restore value to write
    AND R10, 1  ; Mask to 1 bits
    SHL R10, 42  ; Shift to position
    OR RAX, R10  ; Insert new value
    MOVQ xmm15, RAX  ; Store back to SIMD register
    MOV RAX, 2
    ; Zero-latency write to packed variable counter_2bit
    PUSH RAX  ; Save value to write
    MOVQ RAX, xmm15  ; Load packed register
    MOV R10, 26388279066624
    NOT R10  ; Invert mask
    AND RAX, R10  ; Clear bits for counter_2bit
    POP R10  ; Restore value to write
    AND R10, 3  ; Mask to 2 bits
    SHL R10, 43  ; Shift to position
    OR RAX, R10  ; Insert new value
    MOVQ xmm15, RAX  ; Store back to SIMD register
    MOV RAX, 3
    ; Zero-latency write to packed variable state_3bit
    PUSH RAX  ; Save value to write
    MOVQ RAX, xmm15  ; Load packed register
    MOV R10, 246290604621824
    NOT R10  ; Invert mask
    AND RAX, R10  ; Clear bits for state_3bit
    POP R10  ; Restore value to write
    AND R10, 7  ; Mask to 3 bits
    SHL R10, 45  ; Shift to position
    OR RAX, R10  ; Insert new value
    MOVQ xmm15, RAX  ; Store back to SIMD register
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_generic_interrupt_handler) < 1024
times 1024 - ($ - FUNC_generic_interrupt_handler) db 0x90
%endif

FUNC_timer_callback:
    ; Interrupt callback: using zero-latency SIMD register access
    ; xmm15 contains packed kernel flags (no memory reads)
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 8  ; Allocate stack space for SIMD register
    SUB RSP, 8  ; Allocate stack for all locals
    ; Zero-latency read from packed variable flag_1bit
    MOVQ RAX, xmm15  ; Load packed register
    SHR RAX, 42  ; Shift to extract flag_1bit
    AND RAX, 1  ; Mask to 1 bits
    MOV DWORD [RBP - 8], EAX  ; Store val (32-bit)
    MOV EAX, DWORD [RBP - 8]  ; Load val (32-bit)
    NOT RAX
    ; Zero-latency write to packed variable flag_1bit
    PUSH RAX  ; Save value to write
    MOVQ RAX, xmm15  ; Load packed register
    MOV R10, 4398046511104
    NOT R10  ; Invert mask
    AND RAX, R10  ; Clear bits for flag_1bit
    POP R10  ; Restore value to write
    AND R10, 1  ; Mask to 1 bits
    SHL R10, 42  ; Shift to position
    OR RAX, R10  ; Insert new value
    MOVQ xmm15, RAX  ; Store back to SIMD register
    MOV EAX, DWORD [RBP - 8]  ; Load val (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_timer_callback) < 1024
times 1024 - ($ - FUNC_timer_callback) db 0x90
%endif

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

FUNC_subtract:
    MOV RAX, RDI  ; Load parameter a
    MOV R10, RAX  ; Save left operand
    MOV RAX, RSI  ; Load parameter b
    SUB R10, RAX
    MOV RAX, R10
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_subtract) < 1024
times 1024 - ($ - FUNC_subtract) db 0x90
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

FUNC_divide:
    MOV R10, RDI  ; Use y from register
    MOV RAX, 0
    CMP RAX, R10
    SETE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_2245
    MOV RAX, 0
    RET
    JMP END_IF_2245
ELSE_2245:
END_IF_2245:
    MOV RAX, RDI  ; Load parameter x
    MOV R10, RAX  ; Save left operand
    MOV RAX, RSI  ; Load parameter y
    MOV RCX, RAX  ; Save divisor
    MOV RAX, R10  ; Dividend to RAX
    XOR RDX, RDX  ; Clear RDX for unsigned division
    DIV RCX  ; RAX = RAX / RCX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_divide) < 1024
times 1024 - ($ - FUNC_divide) db 0x90
%endif

FUNC_compare_values:
    MOV R10, RDI  ; Use a from register
    MOV RAX, RSI  ; Load parameter b
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_2271
    MOV RAX, 1
    NEG RAX
    RET
    JMP END_IF_2271
ELSE_2271:
    MOV R10, RDI  ; Use a from register
    MOV RAX, RSI  ; Load parameter b
    CMP RAX, R10
    SETE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_2283
    MOV RAX, 0
    RET
    JMP END_IF_2283
ELSE_2283:
    MOV RAX, 1
    RET
END_IF_2283:
END_IF_2271:
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_compare_values) < 1024
times 1024 - ($ - FUNC_compare_values) db 0x90
%endif

FUNC_abs_value:
    MOV R10, RDI  ; Use x from register
    MOV RAX, 0
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_2305
    MOV RAX, RDI  ; Load parameter x
    NEG RAX
    RET
    JMP END_IF_2305
ELSE_2305:
END_IF_2305:
    MOV RAX, RDI  ; Load parameter x
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_abs_value) < 1024
times 1024 - ($ - FUNC_abs_value) db 0x90
%endif

FUNC_max:
    MOV R10, RDI  ; Use a from register
    MOV RAX, RSI  ; Load parameter b
    CMP RAX, R10
    SETG AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_2326
    MOV RAX, RDI  ; Load parameter a
    RET
    JMP END_IF_2326
ELSE_2326:
END_IF_2326:
    MOV RAX, RSI  ; Load parameter b
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_max) < 1024
times 1024 - ($ - FUNC_max) db 0x90
%endif

FUNC_min:
    MOV R10, RDI  ; Use a from register
    MOV RAX, RSI  ; Load parameter b
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_2346
    MOV RAX, RDI  ; Load parameter a
    RET
    JMP END_IF_2346
ELSE_2346:
END_IF_2346:
    MOV RAX, RSI  ; Load parameter b
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_min) < 1024
times 1024 - ($ - FUNC_min) db 0x90
%endif

FUNC_power2:
    MOV R10, RDI  ; Use n from register
    MOV RAX, 0
    CMP R10, RAX
    SETLE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_2366
    MOV RAX, 1
    RET
    JMP END_IF_2366
ELSE_2366:
END_IF_2366:
    MOV RAX, RDI  ; Load parameter n
    SUB RAX, 1
    MOV RDI, RAX
    ; Single call to power2 (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 46  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ADD RAX, RAX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_power2) < 1024
times 1024 - ($ - FUNC_power2) db 0x90
%endif

FUNC_modulo:
    MOV R10, RSI  ; Use b from register
    MOV RAX, 0
    CMP RAX, R10
    SETE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_2395
    MOV RAX, 0
    RET
    JMP END_IF_2395
ELSE_2395:
END_IF_2395:
    MOV R10, RDI  ; Use a from register
    MOV R10, RDI  ; Use a from register
    MOV RAX, RSI  ; Load parameter b
    MOV RCX, RAX  ; Save divisor
    MOV RAX, R10  ; Dividend to RAX
    XOR RDX, RDX  ; Clear RDX for unsigned division
    DIV RCX  ; RAX = RAX / RCX
    MOV R10, RAX  ; Save left operand
    MOV RAX, RSI  ; Load parameter b
    MUL R10
    SUB R10, RAX
    MOV RAX, R10
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_modulo) < 1024
times 1024 - ($ - FUNC_modulo) db 0x90
%endif

FUNC_test_compound_assignment:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 8  ; Allocate stack for all locals
    MOV RAX, RDI  ; Load parameter a
    MOV EBX, EAX  ; Initialize result in register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    PUSH RAX  ; Save current value
    MOV RAX, RSI  ; Load parameter b
    POP R10  ; Get current value
    ADD RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    PUSH RAX  ; Save current value
    MOV RAX, RDI  ; Load parameter a
    POP R10  ; Get current value
    SUB R10, RAX
    MOV RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    PUSH RAX  ; Save current value
    MOV RAX, 2
    POP R10  ; Get current value
    MUL R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    PUSH RAX  ; Save current value
    MOV RAX, 2
    POP R10  ; Get current value
    MOV RCX, RAX  ; Save divisor
    MOV RAX, R10  ; Dividend
    XOR RDX, RDX
    DIV RCX
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    PUSH RAX  ; Save current value
    MOV RAX, 7
    POP R10  ; Get current value
    MOV RCX, RAX  ; Save divisor
    MOV RAX, R10  ; Dividend
    XOR RDX, RDX
    DIV RCX
    MOV RAX, RDX  ; Remainder
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_compound_assignment) < 1024
times 1024 - ($ - FUNC_test_compound_assignment) db 0x90
%endif

FUNC_test_increment_decrement:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 56  ; Allocate stack for all locals
    MOV RAX, RDI  ; Load parameter a
    MOV EBX, EAX  ; Initialize x in register RBX (32-bit)
    MOV RAX, RDI  ; Load parameter a
    MOV R8D, EAX  ; Initialize y in register R8 (32-bit)
    MOV EAX, EBX  ; Load x from register RBX (32-bit)
    MOV RAX, [GLOBAL_x]
    INC RAX
    MOV [GLOBAL_x], RAX
    MOV DWORD [RBP - 24], EAX  ; Store pre_inc (32-bit)
    MOV EAX, R8D  ; Load y from register R8 (32-bit)
    MOV RAX, [GLOBAL_y]
    PUSH RAX  ; Save original value
    INC RAX
    MOV [GLOBAL_y], RAX
    POP RAX  ; Return original value
    MOV DWORD [RBP - 32], EAX  ; Store post_inc (32-bit)
    MOV EAX, EBX  ; Load x from register RBX (32-bit)
    MOV RAX, [GLOBAL_x]
    DEC RAX
    MOV [GLOBAL_x], RAX
    MOV DWORD [RBP - 40], EAX  ; Store pre_dec (32-bit)
    MOV EAX, R8D  ; Load y from register R8 (32-bit)
    MOV RAX, [GLOBAL_y]
    PUSH RAX  ; Save original value
    DEC RAX
    MOV [GLOBAL_y], RAX
    POP RAX  ; Return original value
    MOV DWORD [RBP - 48], EAX  ; Store post_dec (32-bit)
    MOV EAX, DWORD [RBP - 24]  ; Load pre_inc (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 32]  ; Load post_inc (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 40]  ; Load pre_dec (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 48]  ; Load post_dec (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, EBX  ; Load x from register RBX (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, R8D  ; Load y from register R8 (32-bit)
    ADD RAX, R10
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_increment_decrement) < 1024
times 1024 - ($ - FUNC_test_increment_decrement) db 0x90
%endif

FUNC_test_ternary:
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 24  ; Allocate stack for all locals
    MOV R10, RDI  ; Use a from register
    MOV RAX, RSI  ; Load parameter b
    CMP RAX, R10
    SETG AL
    MOVZX RAX, AL
    TEST RAX, RAX  ; Check condition
    JZ TERNARY_FALSE_2
    MOV RAX, RDI  ; Load parameter a
    JMP TERNARY_END_2
TERNARY_FALSE_2:
    MOV RAX, RSI  ; Load parameter b
TERNARY_END_2:
    MOV DWORD [RBP - 8], EAX  ; Store max (32-bit)
    MOV R10, RDI  ; Use a from register
    MOV RAX, RSI  ; Load parameter b
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX  ; Check condition
    JZ TERNARY_FALSE_3
    MOV RAX, RDI  ; Load parameter a
    JMP TERNARY_END_3
TERNARY_FALSE_3:
    MOV RAX, RSI  ; Load parameter b
TERNARY_END_3:
    MOV DWORD [RBP - 16], EAX  ; Store min (32-bit)
    MOV R10, RDI  ; Use a from register
    MOV RAX, 0
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX  ; Check condition
    JZ TERNARY_FALSE_4
    MOV RAX, RDI  ; Load parameter a
    NEG RAX
    JMP TERNARY_END_4
TERNARY_FALSE_4:
    MOV RAX, RDI  ; Load parameter a
TERNARY_END_4:
    MOV DWORD [RBP - 24], EAX  ; Store abs (32-bit)
    MOV EAX, DWORD [RBP - 8]  ; Load max (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 16]  ; Load min (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 24]  ; Load abs (32-bit)
    ADD RAX, R10
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_ternary) < 1024
times 1024 - ($ - FUNC_test_ternary) db 0x90
%endif

FUNC_test_nested_ternary:
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 8  ; Allocate stack for all locals
    MOV R10, RDI  ; Use a from register
    MOV RAX, RSI  ; Load parameter b
    CMP RAX, R10
    SETG AL
    MOVZX RAX, AL
    TEST RAX, RAX  ; Check condition
    JZ TERNARY_FALSE_5
    MOV R10, RDI  ; Use a from register
    MOV RAX, RDX  ; Load parameter c
    CMP RAX, R10
    SETG AL
    MOVZX RAX, AL
    TEST RAX, RAX  ; Check condition
    JZ TERNARY_FALSE_6
    MOV RAX, RDI  ; Load parameter a
    JMP TERNARY_END_6
TERNARY_FALSE_6:
    MOV RAX, RDX  ; Load parameter c
TERNARY_END_6:
    JMP TERNARY_END_5
TERNARY_FALSE_5:
    MOV R10, RSI  ; Use b from register
    MOV RAX, RDX  ; Load parameter c
    CMP RAX, R10
    SETG AL
    MOVZX RAX, AL
    TEST RAX, RAX  ; Check condition
    JZ TERNARY_FALSE_7
    MOV RAX, RSI  ; Load parameter b
    JMP TERNARY_END_7
TERNARY_FALSE_7:
    MOV RAX, RDX  ; Load parameter c
TERNARY_END_7:
TERNARY_END_5:
    MOV DWORD [RBP - 8], EAX  ; Store result (32-bit)
    MOV EAX, DWORD [RBP - 8]  ; Load result (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_nested_ternary) < 1024
times 1024 - ($ - FUNC_test_nested_ternary) db 0x90
%endif

FUNC_test_ternary_with_ops:
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 8  ; Allocate stack for all locals
    MOV R10, RDI  ; Use a from register
    MOV RAX, RSI  ; Load parameter b
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV RAX, 10
    CMP RAX, R10
    SETG AL
    MOVZX RAX, AL
    TEST RAX, RAX  ; Check condition
    JZ TERNARY_FALSE_8
    MOV RAX, RDI  ; Load parameter a
    ADD RAX, RAX
    JMP TERNARY_END_8
TERNARY_FALSE_8:
    MOV RAX, RSI  ; Load parameter b
    ADD RAX, RAX
TERNARY_END_8:
    MOV DWORD [RBP - 8], EAX  ; Store result (32-bit)
    MOV EAX, DWORD [RBP - 8]  ; Load result (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_ternary_with_ops) < 1024
times 1024 - ($ - FUNC_test_ternary_with_ops) db 0x90
%endif

FUNC_test_combined_operators:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 8  ; Allocate stack for all locals
    MOV RAX, RDI  ; Load parameter a
    MOV EBX, EAX  ; Initialize result in register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    PUSH RAX  ; Save current value
    MOV RAX, RSI  ; Load parameter b
    POP R10  ; Get current value
    ADD RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    PUSH RAX  ; Save current value
    MOV RAX, 1
    POP R10  ; Get current value
    MOV RCX, RAX  ; Shift amount
    MOV RAX, R10  ; Value to shift
    SHL RAX, CL
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    PUSH RAX  ; Save current value
    MOV RAX, 255
    POP R10  ; Get current value
    AND RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    PUSH RAX  ; Save current value
    MOV RAX, 128
    POP R10  ; Get current value
    OR RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    PUSH RAX  ; Save current value
    MOV RAX, 64
    POP R10  ; Get current value
    XOR RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    INC RAX
    MOV DWORD [RBP - 8], EAX  ; Store result
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    PUSH RAX  ; Save original value
    INC RAX
    MOV DWORD [RBP - 8], EAX  ; Store result
    MOV EBX, EAX  ; Update result in register RBX (32-bit)
    POP RAX  ; Return original value
    MOV R10, RBX  ; Use result from register
    MOV RAX, 100
    CMP RAX, R10
    SETG AL
    MOVZX RAX, AL
    TEST RAX, RAX  ; Check condition
    JZ TERNARY_FALSE_9
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    SUB RAX, 50
    JMP TERNARY_END_9
TERNARY_FALSE_9:
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    ADD RAX, 50
TERNARY_END_9:
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_combined_operators) < 1024
times 1024 - ($ - FUNC_test_combined_operators) db 0x90
%endif

FUNC_test_complex_expression:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 24  ; Allocate stack for all locals
    MOV RAX, RDI  ; Load parameter a
    MOV DWORD [RBP - 8], EAX  ; Store x (32-bit)
    MOV RAX, RSI  ; Load parameter b
    MOV DWORD [RBP - 16], EAX  ; Store y (32-bit)
    MOV EAX, DWORD [RBP - 8]  ; Load x (32-bit)
    MOV RAX, [GLOBAL_x]
    PUSH RAX  ; Save original value
    INC RAX
    MOV [GLOBAL_x], RAX
    POP RAX  ; Return original value
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 16]  ; Load y (32-bit)
    MOV RAX, [GLOBAL_y]
    INC RAX
    MOV [GLOBAL_y], RAX
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV RAX, 2
    ; Left shift: R10 << RAX
    MOV RCX, RAX  ; Shift amount in RCX
    MOV RAX, R10  ; Value to shift
    SHL RAX, CL  ; Left shift by CL (low 8 bits of RCX)
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 8]  ; Load x (32-bit)
    MOV RAX, [GLOBAL_x]
    PUSH RAX  ; Save original value
    DEC RAX
    MOV [GLOBAL_x], RAX
    POP RAX  ; Return original value
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 16]  ; Load y (32-bit)
    MOV RAX, [GLOBAL_y]
    DEC RAX
    MOV [GLOBAL_y], RAX
    SUB R10, RAX
    MOV RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV RAX, 1
    ; Right shift: R10 >> RAX
    MOV RCX, RAX  ; Shift amount in RCX
    MOV RAX, R10  ; Value to shift
    SHR RAX, CL  ; Right shift by CL (low 8 bits of RCX)
    ; Bitwise AND: R10 & RAX
    AND RAX, R10
    MOV EBX, EAX  ; Initialize result in register RBX (32-bit)
    MOV R10, RBX  ; Use result from register
    MOV RAX, 0
    CMP RAX, R10
    SETG AL
    MOVZX RAX, AL
    TEST RAX, RAX  ; Check condition
    JZ TERNARY_FALSE_10
    MOV R10, RBX  ; Use result from register
    MOV RAX, 255
    ; Bitwise OR: R10 | RAX
    OR RAX, R10
    JMP TERNARY_END_10
TERNARY_FALSE_10:
    MOV R10, RBX  ; Use result from register
    MOV RAX, 0
    ; Bitwise AND: R10 & RAX
    AND RAX, R10
TERNARY_END_10:
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    PUSH RAX  ; Save current value
    MOV RAX, RDX  ; Load parameter c
    POP R10  ; Get current value
    ADD RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    PUSH RAX  ; Save current value
    MOV RAX, 2
    POP R10  ; Get current value
    MUL R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    PUSH RAX  ; Save current value
    MOV RAX, 256
    POP R10  ; Get current value
    MOV RCX, RAX  ; Save divisor
    MOV RAX, R10  ; Dividend
    XOR RDX, RDX
    DIV RCX
    MOV RAX, RDX  ; Remainder
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_complex_expression) < 1024
times 1024 - ($ - FUNC_test_complex_expression) db 0x90
%endif

FUNC_test_address_of:
    LEA RAX, [rel GLOBAL_a]  ; Address of global variable (PIC)
    MOV EDI, EAX  ; Store ptr to register RDI (32-bit)
    MOV RAX, RSI  ; Load parameter ptr
    ; Pointer dereference: *ptr
    MOV RAX, [RAX]  ; Load value at address in RAX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_address_of) < 1024
times 1024 - ($ - FUNC_test_address_of) db 0x90
%endif

FUNC_test_pointer_increment:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 24  ; Allocate stack for all locals
    MOV RAX, 0
    MOV R9D, EAX  ; Initialize sum in register R9 (32-bit)
    MOV RAX, RDI  ; Load parameter arr
    MOV DWORD [RBP - 16], EAX  ; Store p (32-bit)
    MOV RAX, 0
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
FOR_2941:
    MOV R10, RBX  ; Use i from register
    MOV RAX, RSI  ; Load parameter len
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ END_FOR_2941
    MOV EAX, R9D  ; Load sum from register R9 (32-bit)
    PUSH RAX  ; Save current value
    MOV EAX, DWORD [RBP - 16]  ; Load p (32-bit)
    ; Pointer dereference: *ptr
    MOV RAX, [RAX]  ; Load value at address in RAX
    POP R10  ; Get current value
    ADD RAX, R10
    MOV R9D, EAX  ; Store sum to register R9 (32-bit)
    MOV EAX, DWORD [RBP - 16]  ; Load p (32-bit)
    MOV EAX, DWORD [RBP - 16]  ; Load p (32-bit)
    PUSH RAX  ; Save original value
    INC RAX
    MOV DWORD [RBP - 16], EAX  ; Store p
    POP RAX  ; Return original value
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    ADD RAX, 1
    MOV EBX, EAX  ; Store i to register RBX (32-bit)
    JMP FOR_2941
END_FOR_2941:
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
%if ($ - FUNC_test_pointer_increment) < 1024
times 1024 - ($ - FUNC_test_pointer_increment) db 0x90
%endif

FUNC_init_point:
    MOV RBX, RDI  ; Get struct pointer p
    MOV RAX, RSI  ; Load parameter x
    MOV DWORD [RBX], EAX  ; Store to struct member x
    MOV RBX, RDI  ; Get struct pointer p
    ADD RBX, 4  ; Add member offset for y
    MOV RAX, RDX  ; Load parameter y
    MOV DWORD [RBX], EAX  ; Store to struct member y
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_init_point) < 1024
times 1024 - ($ - FUNC_init_point) db 0x90
%endif

FUNC_get_point_x:
    MOV RAX, RDI  ; Get struct pointer p
    ; Struct member access: x at offset 0
    MOV RAX, [RAX]  ; Load member value
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_get_point_x) < 1024
times 1024 - ($ - FUNC_get_point_x) db 0x90
%endif

FUNC_get_point_y:
    MOV RAX, RDI  ; Get struct pointer p
    ; Struct member access: y at offset 4
    ADD RAX, 4  ; Add member offset
    MOV RAX, [RAX]  ; Load member value
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_get_point_y) < 1024
times 1024 - ($ - FUNC_get_point_y) db 0x90
%endif

FUNC_set_point:
    MOV RBX, RDI  ; Get struct pointer p
    MOV RAX, RSI  ; Load parameter x
    MOV DWORD [RBX], EAX  ; Store to struct member x
    MOV RBX, RDI  ; Get struct pointer p
    ADD RBX, 4  ; Add member offset for y
    MOV RAX, RDX  ; Load parameter y
    MOV DWORD [RBX], EAX  ; Store to struct member y
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_set_point) < 1024
times 1024 - ($ - FUNC_set_point) db 0x90
%endif

FUNC_point_distance_squared:
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 24  ; Allocate stack for all locals
    MOV RAX, RDI  ; Get struct pointer p1
    ; Struct member access: x at offset 0
    MOV RAX, [RAX]  ; Load member value
    MOV R10, RAX  ; Save left operand
    MOV RAX, RSI  ; Get struct pointer p2
    ; Struct member access: x at offset 0
    MOV RAX, [RAX]  ; Load member value
    SUB R10, RAX
    MOV RAX, R10
    MOV DWORD [RBP - 8], EAX  ; Store dx (32-bit)
    MOV RAX, RDI  ; Get struct pointer p1
    ; Struct member access: y at offset 4
    ADD RAX, 4  ; Add member offset
    MOV RAX, [RAX]  ; Load member value
    MOV R10, RAX  ; Save left operand
    MOV RAX, RSI  ; Get struct pointer p2
    ; Struct member access: y at offset 4
    ADD RAX, 4  ; Add member offset
    MOV RAX, [RAX]  ; Load member value
    SUB R10, RAX
    MOV RAX, R10
    MOV DWORD [RBP - 16], EAX  ; Store dy (32-bit)
    MOV EAX, DWORD [RBP - 8]  ; Load dx (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 8]  ; Load dx (32-bit)
    MUL R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 16]  ; Load dy (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 16]  ; Load dy (32-bit)
    MUL R10
    ADD RAX, R10
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_point_distance_squared) < 1024
times 1024 - ($ - FUNC_point_distance_squared) db 0x90
%endif

FUNC_init_rectangle:
    MOV RBX, RDI  ; Get struct pointer r
    MOV RAX, RSI  ; Load parameter x
    MOV DWORD [RBX], EAX  ; Store to struct member x
    MOV RBX, RDI  ; Get struct pointer r
    ADD RBX, 4  ; Add member offset for y
    MOV RAX, RDX  ; Load parameter y
    MOV DWORD [RBX], EAX  ; Store to struct member y
    MOV RBX, RDI  ; Get struct pointer r
    ADD RBX, 8  ; Add member offset for width
    MOV RAX, RCX  ; Load parameter w
    MOV DWORD [RBX], EAX  ; Store to struct member width
    MOV RBX, RDI  ; Get struct pointer r
    ADD RBX, 12  ; Add member offset for height
    MOV RAX, R8  ; Load parameter h
    MOV DWORD [RBX], EAX  ; Store to struct member height
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_init_rectangle) < 1024
times 1024 - ($ - FUNC_init_rectangle) db 0x90
%endif

FUNC_rectangle_area:
    MOV RAX, RDI  ; Get struct pointer r
    ; Struct member access: width at offset 8
    ADD RAX, 8  ; Add member offset
    MOV RAX, [RAX]  ; Load member value
    MOV R10, RAX  ; Save left operand
    MOV RAX, RDI  ; Get struct pointer r
    ; Struct member access: height at offset 12
    ADD RAX, 12  ; Add member offset
    MOV RAX, [RAX]  ; Load member value
    MUL R10
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_rectangle_area) < 1024
times 1024 - ($ - FUNC_rectangle_area) db 0x90
%endif

FUNC_point_in_rectangle:
    MOV RAX, RSI  ; Get struct pointer p
    ; Struct member access: x at offset 0
    MOV RAX, [RAX]  ; Load member value
    MOV R10, RAX  ; Save left operand
    MOV RAX, RDI  ; Get struct pointer r
    ; Struct member access: x at offset 0
    MOV RAX, [RAX]  ; Load member value
    CMP RAX, R10
    SETGE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_3126
    MOV RAX, RSI  ; Get struct pointer p
    ; Struct member access: x at offset 0
    MOV RAX, [RAX]  ; Load member value
    MOV R10, RAX  ; Save left operand
    MOV RAX, RDI  ; Get struct pointer r
    ; Struct member access: x at offset 0
    MOV RAX, [RAX]  ; Load member value
    MOV R10, RAX  ; Save left operand
    MOV RAX, RDI  ; Get struct pointer r
    ; Struct member access: width at offset 8
    ADD RAX, 8  ; Add member offset
    MOV RAX, [RAX]  ; Load member value
    ADD RAX, R10
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_3126
    MOV RAX, RSI  ; Get struct pointer p
    ; Struct member access: y at offset 4
    ADD RAX, 4  ; Add member offset
    MOV RAX, [RAX]  ; Load member value
    MOV R10, RAX  ; Save left operand
    MOV RAX, RDI  ; Get struct pointer r
    ; Struct member access: y at offset 4
    ADD RAX, 4  ; Add member offset
    MOV RAX, [RAX]  ; Load member value
    CMP RAX, R10
    SETGE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_3156
    MOV RAX, RSI  ; Get struct pointer p
    ; Struct member access: y at offset 4
    ADD RAX, 4  ; Add member offset
    MOV RAX, [RAX]  ; Load member value
    MOV R10, RAX  ; Save left operand
    MOV RAX, RDI  ; Get struct pointer r
    ; Struct member access: y at offset 4
    ADD RAX, 4  ; Add member offset
    MOV RAX, [RAX]  ; Load member value
    MOV R10, RAX  ; Save left operand
    MOV RAX, RDI  ; Get struct pointer r
    ; Struct member access: height at offset 12
    ADD RAX, 12  ; Add member offset
    MOV RAX, [RAX]  ; Load member value
    ADD RAX, R10
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_3156
    MOV RAX, 1
    RET
    JMP END_IF_3156
ELSE_3156:
END_IF_3156:
    JMP END_IF_3126
ELSE_3126:
END_IF_3126:
    MOV RAX, 0
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_point_in_rectangle) < 1024
times 1024 - ($ - FUNC_point_in_rectangle) db 0x90
%endif

FUNC_move_rectangle:
    MOV RAX, RDI  ; Load parameter r
    MOV RBX, RAX  ; Save member address in RBX
    MOV EAX, DWORD [RBX]  ; Load current value from member
    PUSH RBX  ; Save member address for later store
    PUSH RAX  ; Save current value
    MOV RAX, RSI  ; Load parameter dx
    POP R10  ; Get current value
    ADD RAX, R10
    POP R10  ; Get member address back
    MOV DWORD [R10], EAX  ; Store result to member
    MOV RAX, RDI  ; Load parameter r
    ADD RAX, 4
    MOV RBX, RAX  ; Save member address in RBX
    MOV EAX, DWORD [RBX]  ; Load current value from member
    PUSH RBX  ; Save member address for later store
    PUSH RAX  ; Save current value
    MOV RAX, RDX  ; Load parameter dy
    POP R10  ; Get current value
    ADD RAX, R10
    POP R10  ; Get member address back
    MOV DWORD [R10], EAX  ; Store result to member
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_move_rectangle) < 1024
times 1024 - ($ - FUNC_move_rectangle) db 0x90
%endif

FUNC_resize_rectangle:
    MOV RAX, RDI  ; Load parameter r
    ADD RAX, 8
    MOV RBX, RAX  ; Save member address in RBX
    MOV EAX, DWORD [RBX]  ; Load current value from member
    PUSH RBX  ; Save member address for later store
    PUSH RAX  ; Save current value
    MOV RAX, RSI  ; Load parameter dw
    POP R10  ; Get current value
    ADD RAX, R10
    POP R10  ; Get member address back
    MOV DWORD [R10], EAX  ; Store result to member
    MOV RAX, RDI  ; Load parameter r
    ADD RAX, 12
    MOV RBX, RAX  ; Save member address in RBX
    MOV EAX, DWORD [RBX]  ; Load current value from member
    PUSH RBX  ; Save member address for later store
    PUSH RAX  ; Save current value
    MOV RAX, RDX  ; Load parameter dh
    POP R10  ; Get current value
    ADD RAX, R10
    POP R10  ; Get member address back
    MOV DWORD [R10], EAX  ; Store result to member
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_resize_rectangle) < 1024
times 1024 - ($ - FUNC_resize_rectangle) db 0x90
%endif

FUNC_test_struct_operations:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 56  ; Allocate stack for all locals
    XOR R8D, R8D  ; Initialize p1 to 0 in register R8 (32-bit)
    XOR RAX, RAX  ; Initialize p2 to 0
    MOV DWORD [RBP - 16], EAX  ; Store p2 (32-bit)
    XOR EBX, EBX  ; Initialize rect to 0 in register RBX (32-bit)
    LEA RAX, [RBP - 8]  ; Address of local variable p1
    MOV RDI, RAX
    MOV RAX, 10
    MOV RSI, RAX
    MOV RAX, 20
    MOV RDX, RAX
    ; Single call to init_point (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 57  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_test_struct_operations_0:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 0 (stored in single byte)
    LEA RAX, [RBP - 16]  ; Address of local variable p2
    MOV RDI, RAX
    MOV RAX, 30
    MOV RSI, RAX
    MOV RAX, 40
    MOV RDX, RAX
    ; Single call to init_point (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 57  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_test_struct_operations_1:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 1 (stored in single byte)
    LEA RAX, [RBP - 32]  ; Address of local variable rect
    MOV RDI, RAX
    MOV RAX, 0
    MOV RSI, RAX
    MOV RAX, 0
    MOV RDX, RAX
    MOV RAX, 100
    MOV RCX, RAX
    MOV RAX, 200
    MOV R8, RAX
    ; Single call to init_rectangle (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 62  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_test_struct_operations_2:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 2 (stored in single byte)
    LEA RAX, [RBP - 8]  ; Address of local variable p1
    MOV RDI, RAX
    LEA RAX, [RBP - 16]  ; Address of local variable p2
    MOV RSI, RAX
    ; Single call to point_distance_squared (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 61  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_test_struct_operations_3:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 3 (stored in single byte)
    MOV DWORD [RBP - 40], EAX  ; Store dist (32-bit)
    LEA RAX, [RBP - 32]  ; Address of local variable rect
    MOV RDI, RAX
    ; Single call to rectangle_area (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 63  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_test_struct_operations_4:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 4 (stored in single byte)
    MOV DWORD [RBP - 48], EAX  ; Store area (32-bit)
    LEA RAX, [RBP - 32]  ; Address of local variable rect
    MOV RDI, RAX
    LEA RAX, [RBP - 8]  ; Address of local variable p1
    MOV RSI, RAX
    ; Single call to point_in_rectangle (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 64  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    MOV DWORD [RBP - 56], EAX  ; Store inside (32-bit)
    LEA RAX, [RBP - 32]  ; Address of local variable rect
    MOV RDI, RAX
    MOV RAX, 5
    MOV RSI, RAX
    MOV RAX, 10
    MOV RDX, RAX
    ; Single call to move_rectangle (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 65  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_test_struct_operations_5:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 5 (stored in single byte)
    LEA RAX, [RBP - 32]  ; Address of local variable rect
    MOV RDI, RAX
    MOV RAX, 20
    MOV RSI, RAX
    MOV RAX, 30
    MOV RDX, RAX
    ; Single call to resize_rectangle (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 66  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_test_struct_operations_6:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 6 (stored in single byte)
    MOV EAX, DWORD [RBP - 40]  ; Load dist (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 48]  ; Load area (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 56]  ; Load inside (32-bit)
    ADD RAX, R10
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_struct_operations) < 1024
times 1024 - ($ - FUNC_test_struct_operations) db 0x90
%endif

FUNC_test_binary_ops:
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 104  ; Allocate stack for all locals
    MOV R10, RDI  ; Use a from register
    MOV RAX, RSI  ; Load parameter b
    ADD RAX, R10
    MOV DWORD [RBP - 8], EAX  ; Store add_result (32-bit)
    MOV R10, RDI  ; Use a from register
    MOV RAX, RSI  ; Load parameter b
    SUB R10, RAX
    MOV RAX, R10
    MOV DWORD [RBP - 16], EAX  ; Store sub_result (32-bit)
    MOV R10, RDI  ; Use a from register
    MOV RAX, RSI  ; Load parameter b
    MUL R10
    MOV DWORD [RBP - 24], EAX  ; Store mul_result (32-bit)
    MOV RAX, 0
    MOV DWORD [RBP - 32], EAX  ; Store div_result (32-bit)
    MOV R10, RSI  ; Use b from register
    MOV RAX, 0
    CMP RAX, R10
    SETNE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_3436
    MOV R10, RDI  ; Use a from register
    MOV RAX, RSI  ; Load parameter b
    MOV RCX, RAX  ; Save divisor
    MOV RAX, R10  ; Dividend to RAX
    XOR RDX, RDX  ; Clear RDX for unsigned division
    DIV RCX  ; RAX = RAX / RCX
    MOV DWORD [RBP - 32], EAX  ; Store div_result (32-bit)
    JMP END_IF_3436
ELSE_3436:
END_IF_3436:
    MOV RAX, 0
    MOV DWORD [RBP - 40], EAX  ; Store mod_result (32-bit)
    MOV R10, RSI  ; Use b from register
    MOV RAX, 0
    CMP RAX, R10
    SETNE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_3455
    MOV R10, RDI  ; Use a from register
    MOV RAX, RSI  ; Load parameter b
    ; Modulo operation: R10 % RAX
    PUSH RAX  ; Save right operand (divisor)
    MOV RAX, R10  ; Move left operand (dividend) to RAX
    POP R10  ; Get divisor
    XOR RDX, RDX  ; Clear RDX for division
    DIV R10  ; RAX = dividend / divisor, RDX = remainder
    MOV RAX, RDX  ; Remainder is the modulo result
    MOV DWORD [RBP - 40], EAX  ; Store mod_result (32-bit)
    JMP END_IF_3455
ELSE_3455:
END_IF_3455:
    MOV R10, RDI  ; Use a from register
    MOV RAX, RSI  ; Load parameter b
    CMP RAX, R10
    SETE AL
    MOVZX RAX, AL
    MOV DWORD [RBP - 48], EAX  ; Store eq_result (32-bit)
    MOV R10, RDI  ; Use a from register
    MOV RAX, RSI  ; Load parameter b
    CMP RAX, R10
    SETNE AL
    MOVZX RAX, AL
    MOV DWORD [RBP - 56], EAX  ; Store ne_result (32-bit)
    MOV R10, RDI  ; Use a from register
    MOV RAX, RSI  ; Load parameter b
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    MOV DWORD [RBP - 64], EAX  ; Store lt_result (32-bit)
    MOV R10, RDI  ; Use a from register
    MOV RAX, RSI  ; Load parameter b
    CMP RAX, R10
    SETG AL
    MOVZX RAX, AL
    MOV DWORD [RBP - 72], EAX  ; Store gt_result (32-bit)
    MOV R10, RDI  ; Use a from register
    MOV RAX, RSI  ; Load parameter b
    CMP R10, RAX
    SETLE AL
    MOVZX RAX, AL
    MOV DWORD [RBP - 80], EAX  ; Store le_result (32-bit)
    MOV R10, RDI  ; Use a from register
    MOV RAX, RSI  ; Load parameter b
    CMP RAX, R10
    SETGE AL
    MOVZX RAX, AL
    MOV DWORD [RBP - 88], EAX  ; Store ge_result (32-bit)
    MOV R10, RDI  ; Use a from register
    MOV RAX, 0
    CMP RAX, R10
    SETG AL
    MOVZX RAX, AL
    MOV R10, RAX  ; Save left operand
    MOV R10, RSI  ; Use b from register
    MOV RAX, 0
    CMP RAX, R10
    SETG AL
    MOVZX RAX, AL
    ; Logical AND: R10 && RAX
    TEST R10, R10  ; Check if left is non-zero
    JZ AND_FALSE_11
    TEST RAX, RAX  ; Check if right is non-zero
    JZ AND_FALSE_11
    MOV RAX, 1  ; Both non-zero, result is 1
    JMP AND_END_11
AND_FALSE_11:
    MOV RAX, 0  ; One or both zero, result is 0
AND_END_11:
    MOV DWORD [RBP - 96], EAX  ; Store and_result (32-bit)
    MOV R10, RDI  ; Use a from register
    MOV RAX, 0
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    MOV R10, RAX  ; Save left operand
    MOV R10, RSI  ; Use b from register
    MOV RAX, 0
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    ; Logical OR: R10 || RAX
    TEST R10, R10  ; Check if left is non-zero
    JNZ OR_TRUE_12
    TEST RAX, RAX  ; Check if right is non-zero
    JNZ OR_TRUE_12
    MOV RAX, 0  ; Both zero, result is 0
    JMP OR_END_12
OR_TRUE_12:
    MOV RAX, 1  ; At least one non-zero, result is 1
OR_END_12:
    MOV DWORD [RBP - 104], EAX  ; Store or_result (32-bit)
    MOV EAX, DWORD [RBP - 8]  ; Load add_result (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 16]  ; Load sub_result (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 24]  ; Load mul_result (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 32]  ; Load div_result (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 40]  ; Load mod_result (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 48]  ; Load eq_result (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 56]  ; Load ne_result (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 64]  ; Load lt_result (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 72]  ; Load gt_result (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 80]  ; Load le_result (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 88]  ; Load ge_result (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 96]  ; Load and_result (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 104]  ; Load or_result (32-bit)
    ADD RAX, R10
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_binary_ops) < 1024
times 1024 - ($ - FUNC_test_binary_ops) db 0x90
%endif

FUNC_test_unary_ops:
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 24  ; Allocate stack for all locals
    MOV RAX, RDI  ; Load parameter x
    NEG RAX
    MOV DWORD [RBP - 8], EAX  ; Store neg (32-bit)
    MOV RAX, RDI  ; Load parameter x
    NOT RAX
    MOV DWORD [RBP - 16], EAX  ; Store not_val (32-bit)
    MOV EAX, DWORD [RBP - 8]  ; Load neg (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 16]  ; Load not_val (32-bit)
    ADD RAX, R10
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_unary_ops) < 1024
times 1024 - ($ - FUNC_test_unary_ops) db 0x90
%endif

FUNC_test_complex_expressions:
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 40  ; Allocate stack for all locals
    MOV R10, RDI  ; Use a from register
    MOV RAX, RSI  ; Load parameter b
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV RAX, RDX  ; Load parameter c
    MUL R10
    MOV DWORD [RBP - 8], EAX  ; Store expr1 (32-bit)
    MOV R10, RDI  ; Use a from register
    MOV R10, RSI  ; Use b from register
    MOV RAX, RDX  ; Load parameter c
    SUB R10, RAX
    MOV RAX, R10
    MUL R10
    MOV DWORD [RBP - 16], EAX  ; Store expr2 (32-bit)
    MOV R10, RDI  ; Use a from register
    MOV RAX, RSI  ; Load parameter b
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV RAX, RDX  ; Load parameter c
    ADD RAX, 1
    MOV RCX, RAX  ; Save divisor
    MOV RAX, R10  ; Dividend to RAX
    XOR RDX, RDX  ; Clear RDX for unsigned division
    DIV RCX  ; RAX = RAX / RCX
    MOV DWORD [RBP - 24], EAX  ; Store expr3 (32-bit)
    MOV R10, RDI  ; Use a from register
    MOV RAX, RSI  ; Load parameter b
    MUL R10
    MOV R10, RAX  ; Save left operand
    MOV RAX, RDX  ; Load parameter c
    ADD RAX, RAX
    ADD RAX, R10
    MOV DWORD [RBP - 32], EAX  ; Store expr4 (32-bit)
    MOV EAX, DWORD [RBP - 8]  ; Load expr1 (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 16]  ; Load expr2 (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 24]  ; Load expr3 (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 32]  ; Load expr4 (32-bit)
    ADD RAX, R10
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_complex_expressions) < 1024
times 1024 - ($ - FUNC_test_complex_expressions) db 0x90
%endif

FUNC_nested_calls:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 8  ; Allocate stack for all locals
    MOV RAX, RDI  ; Load parameter x
    MOV RDI, RAX
    MOV RAX, RDI  ; Load parameter x
    ADD RAX, 1
    MOV RSI, RAX
    ; Single call to test_binary_ops (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 68  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_nested_calls_7:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 7 (stored in single byte)
    MOV EBX, EAX  ; Initialize result in register RBX (32-bit)
    MOV R10, RBX  ; Use result from register
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    MOV RDI, RAX
    ; Single call to test_unary_ops (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 69  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_nested_calls_8:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 8 (stored in single byte)
    ADD RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV R10, RBX  ; Use result from register
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    MOV RDI, RAX
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    ADD RAX, 1
    MOV RSI, RAX
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    ADD RAX, 2
    MOV RDX, RAX
    ; Single call to test_complex_expressions (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 70  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_nested_calls_9:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 9 (stored in single byte)
    ADD RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_nested_calls) < 1024
times 1024 - ($ - FUNC_nested_calls) db 0x90
%endif

FUNC_multiple_returns:
    MOV R10, RDI  ; Use x from register
    MOV RAX, 0
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_3773
    MOV RAX, 1
    NEG RAX
    RET
    JMP END_IF_3773
ELSE_3773:
END_IF_3773:
    MOV R10, RDI  ; Use x from register
    MOV RAX, 0
    CMP RAX, R10
    SETE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_3786
    MOV RAX, 0
    RET
    JMP END_IF_3786
ELSE_3786:
END_IF_3786:
    MOV R10, RDI  ; Use x from register
    MOV RAX, 10
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_3798
    MOV RAX, 1
    RET
    JMP END_IF_3798
ELSE_3798:
END_IF_3798:
    MOV R10, RDI  ; Use x from register
    MOV RAX, 100
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_3810
    MOV RAX, 2
    RET
    JMP END_IF_3810
ELSE_3810:
END_IF_3810:
    MOV RAX, 3
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_multiple_returns) < 1024
times 1024 - ($ - FUNC_multiple_returns) db 0x90
%endif

FUNC_single_return:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 8  ; Allocate stack for all locals
    MOV RAX, RDI  ; Load parameter x
    ADD RAX, RAX
    MOV EBX, EAX  ; Initialize result in register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    ADD RAX, 10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_single_return) < 1024
times 1024 - ($ - FUNC_single_return) db 0x90
%endif

FUNC_test_char_constants:
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 24  ; Allocate stack for all locals
    MOV RAX, 65
    MOV DWORD [RBP - 8], EAX  ; Store a (32-bit)
    MOV RAX, 66
    MOV DWORD [RBP - 16], EAX  ; Store b (32-bit)
    MOV RAX, 67
    MOV DWORD [RBP - 24], EAX  ; Store c (32-bit)
    MOV EAX, DWORD [RBP - 8]  ; Load a (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 16]  ; Load b (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 24]  ; Load c (32-bit)
    ADD RAX, R10
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_char_constants) < 1024
times 1024 - ($ - FUNC_test_char_constants) db 0x90
%endif

FUNC_test_numeric_constants:
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 24  ; Allocate stack for all locals
    MOV RAX, 100
    MOV DWORD [RBP - 8], EAX  ; Store dec (32-bit)
    MOV RAX, 255
    MOV DWORD [RBP - 16], EAX  ; Store hex (32-bit)
    MOV RAX, 63
    MOV DWORD [RBP - 24], EAX  ; Store oct (32-bit)
    MOV EAX, DWORD [RBP - 8]  ; Load dec (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 16]  ; Load hex (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 24]  ; Load oct (32-bit)
    ADD RAX, R10
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_numeric_constants) < 1024
times 1024 - ($ - FUNC_test_numeric_constants) db 0x90
%endif

FUNC_test_declarations:
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 40  ; Allocate stack for all locals
    MOV RAX, 10
    MOV DWORD [RBP - 8], EAX  ; Store a (32-bit)
    MOV RAX, 20
    MOV DWORD [RBP - 16], EAX  ; Store b (32-bit)
    MOV EAX, DWORD [RBP - 8]  ; Load a (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 16]  ; Load b (32-bit)
    ADD RAX, R10
    MOV DWORD [RBP - 24], EAX  ; Store c (32-bit)
    MOV EAX, DWORD [RBP - 24]  ; Load c (32-bit)
    ADD RAX, RAX
    MOV DWORD [RBP - 32], EAX  ; Store d (32-bit)
    MOV EAX, DWORD [RBP - 32]  ; Load d (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV RAX, 4
    MOV RCX, RAX  ; Save divisor
    MOV RAX, R10  ; Dividend to RAX
    XOR RDX, RDX  ; Clear RDX for unsigned division
    DIV RCX  ; RAX = RAX / RCX
    MOV DWORD [RBP - 40], EAX  ; Store e (32-bit)
    MOV EAX, DWORD [RBP - 8]  ; Load a (32-bit)
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 16]  ; Load b (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 24]  ; Load c (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 32]  ; Load d (32-bit)
    ADD RAX, R10
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 40]  ; Load e (32-bit)
    ADD RAX, R10
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_declarations) < 1024
times 1024 - ($ - FUNC_test_declarations) db 0x90
%endif

FUNC_test_assignments:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 8  ; Allocate stack for all locals
    MOV RAX, 0
    MOV EBX, EAX  ; Initialize x in register RBX (32-bit)
    MOV RAX, 10
    MOV [GLOBAL_x], RAX
    MOV EAX, EBX  ; Load x from register RBX (32-bit)
    ADD RAX, 5
    MOV [GLOBAL_x], RAX
    MOV EAX, EBX  ; Load x from register RBX (32-bit)
    SUB RAX, 3
    MOV [GLOBAL_x], RAX
    MOV EAX, EBX  ; Load x from register RBX (32-bit)
    ADD RAX, RAX
    MOV [GLOBAL_x], RAX
    MOV R10, RBX  ; Use x from register
    MOV RAX, 4
    MOV RCX, RAX  ; Save divisor
    MOV RAX, R10  ; Dividend to RAX
    XOR RDX, RDX  ; Clear RDX for unsigned division
    DIV RCX  ; RAX = RAX / RCX
    MOV [GLOBAL_x], RAX
    MOV EAX, EBX  ; Load x from register RBX (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_assignments) < 1024
times 1024 - ($ - FUNC_test_assignments) db 0x90
%endif

FUNC_test_mixed_operations:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 8  ; Allocate stack for all locals
    MOV RAX, 0
    MOV EBX, EAX  ; Initialize result in register RBX (32-bit)
    MOV R10, RDI  ; Use a from register
    MOV RAX, RSI  ; Load parameter b
    ADD RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV R10, RBX  ; Use result from register
    MOV RAX, RDX  ; Load parameter c
    SUB R10, RAX
    MOV RAX, R10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    ADD RAX, RAX
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV R10, RBX  ; Use result from register
    MOV RAX, 2
    MOV RCX, RAX  ; Save divisor
    MOV RAX, R10  ; Dividend to RAX
    XOR RDX, RDX  ; Clear RDX for unsigned division
    DIV RCX  ; RAX = RAX / RCX
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV R10, RBX  ; Use result from register
    MOV RAX, 7
    ; Modulo operation: R10 % RAX
    PUSH RAX  ; Save right operand (divisor)
    MOV RAX, R10  ; Move left operand (dividend) to RAX
    POP R10  ; Get divisor
    XOR RDX, RDX  ; Clear RDX for division
    DIV R10  ; RAX = dividend / divisor, RDX = remainder
    MOV RAX, RDX  ; Remainder is the modulo result
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    MOV R10, RBX  ; Use result from register
    MOV RAX, RDI  ; Load parameter a
    CMP RAX, R10
    SETE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_4066
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    ADD RAX, 1
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    JMP END_IF_4066
ELSE_4066:
END_IF_4066:
    MOV R10, RBX  ; Use result from register
    MOV RAX, RSI  ; Load parameter b
    CMP RAX, R10
    SETNE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_4079
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    ADD RAX, 2
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    JMP END_IF_4079
ELSE_4079:
END_IF_4079:
    MOV R10, RBX  ; Use result from register
    MOV RAX, RSI  ; Load parameter b
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_4092
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    ADD RAX, RAX
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    JMP END_IF_4092
ELSE_4092:
END_IF_4092:
    MOV R10, RBX  ; Use result from register
    MOV RAX, RDX  ; Load parameter c
    CMP RAX, R10
    SETG AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_4105
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    SUB RAX, 1
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    JMP END_IF_4105
ELSE_4105:
END_IF_4105:
    MOV R10, RBX  ; Use result from register
    MOV RAX, RDI  ; Load parameter a
    CMP R10, RAX
    SETLE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_4118
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    ADD RAX, 3
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    JMP END_IF_4118
ELSE_4118:
END_IF_4118:
    MOV R10, RBX  ; Use result from register
    MOV RAX, RSI  ; Load parameter b
    CMP RAX, R10
    SETGE AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_4131
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    SUB RAX, 2
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    JMP END_IF_4131
ELSE_4131:
END_IF_4131:
    MOV R10, RBX  ; Use result from register
    MOV RAX, 0
    CMP RAX, R10
    SETG AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_4144
    MOV R10, RBX  ; Use result from register
    MOV RAX, 100
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    TEST RAX, RAX
    JZ ELSE_4144
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    ADD RAX, RAX
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    JMP END_IF_4144
ELSE_4144:
END_IF_4144:
    MOV R10, RBX  ; Use result from register
    MOV RAX, 0
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    MOV R10, RAX  ; Save left operand
    MOV R10, RBX  ; Use result from register
    MOV RAX, 1000
    CMP RAX, R10
    SETG AL
    MOVZX RAX, AL
    ; Logical OR: R10 || RAX
    TEST R10, R10  ; Check if left is non-zero
    JNZ OR_TRUE_13
    TEST RAX, RAX  ; Check if right is non-zero
    JNZ OR_TRUE_13
    MOV RAX, 0  ; Both zero, result is 0
    JMP OR_END_13
OR_TRUE_13:
    MOV RAX, 1  ; At least one non-zero, result is 1
OR_END_13:
    TEST RAX, RAX
    JZ ELSE_4164
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    ADD RAX, 10
    MOV EBX, EAX  ; Store result to register RBX (32-bit)
    JMP END_IF_4164
ELSE_4164:
END_IF_4164:
    MOV EAX, EBX  ; Load result from register RBX (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
    RET
    ; Pad to 1024-byte slot for indexed-jump co-location
%if ($ - FUNC_test_mixed_operations) < 1024
times 1024 - ($ - FUNC_test_mixed_operations) db 0x90
%endif

; SIMD Bit-Packing: Pack global variables (1-8 bits) into last SIMD register
; This register (xmm15) is typically ignored by standard compilers
; Variables declared as 'auto _Alignas(N) char' are packed as N-bit values
_init_simd_packing:
    ; Initialize xmm15 with packed global variables
    PXOR xmm15, xmm15  ; Clear register
    ; Pack flag_1bit at bit 0, width 1 bits
    MOVZX RAX, BYTE [GLOBAL_flag_1bit]  ; Load flag_1bit
    ; Extract and mask to 1 bits
    AND RAX, 1  ; Mask to 1 bits
    MOVQ XMM0, RAX  ; Move to XMM0
    POR xmm15, XMM0  ; OR into packed register
    ; Pack counter_2bit at bit 1, width 2 bits
    MOVZX RAX, BYTE [GLOBAL_counter_2bit]  ; Load counter_2bit
    ; Extract and mask to 2 bits
    AND RAX, 3  ; Mask to 2 bits
    SHL RAX, 1  ; Shift to bit position 1
    MOVQ XMM0, RAX  ; Move to XMM0
    POR xmm15, XMM0  ; OR into packed register
    ; Pack state_3bit at bit 3, width 3 bits
    MOVZX RAX, BYTE [GLOBAL_state_3bit]  ; Load state_3bit
    ; Extract and mask to 3 bits
    AND RAX, 7  ; Mask to 3 bits
    SHL RAX, 3  ; Shift to bit position 3
    MOVQ XMM0, RAX  ; Move to XMM0
    POR xmm15, XMM0  ; OR into packed register
    ; Pack mode_4bit at bit 6, width 4 bits
    MOVZX RAX, BYTE [GLOBAL_mode_4bit]  ; Load mode_4bit
    ; Extract and mask to 4 bits
    AND RAX, 15  ; Mask to 4 bits
    SHL RAX, 6  ; Shift to bit position 6
    MOVQ XMM0, RAX  ; Move to XMM0
    POR xmm15, XMM0  ; OR into packed register
    ; Pack level_5bit at bit 10, width 5 bits
    MOVZX RAX, BYTE [GLOBAL_level_5bit]  ; Load level_5bit
    ; Extract and mask to 5 bits
    AND RAX, 31  ; Mask to 5 bits
    SHL RAX, 10  ; Shift to bit position 10
    MOVQ XMM0, RAX  ; Move to XMM0
    POR xmm15, XMM0  ; OR into packed register
    ; Pack index_6bit at bit 15, width 6 bits
    MOVZX RAX, BYTE [GLOBAL_index_6bit]  ; Load index_6bit
    ; Extract and mask to 6 bits
    AND RAX, 63  ; Mask to 6 bits
    SHL RAX, 15  ; Shift to bit position 15
    MOVQ XMM0, RAX  ; Move to XMM0
    POR xmm15, XMM0  ; OR into packed register
    ; Pack offset_7bit at bit 21, width 7 bits
    MOVZX RAX, BYTE [GLOBAL_offset_7bit]  ; Load offset_7bit
    ; Extract and mask to 7 bits
    AND RAX, 127  ; Mask to 7 bits
    SHL RAX, 21  ; Shift to bit position 21
    MOVQ XMM0, RAX  ; Move to XMM0
    POR xmm15, XMM0  ; OR into packed register
    ; Pack value_8bit at bit 28, width 8 bits
    MOVZX RAX, BYTE [GLOBAL_value_8bit]  ; Load value_8bit
    ; Extract and mask to 8 bits
    AND RAX, 255  ; Mask to 8 bits
    SHL RAX, 28  ; Shift to bit position 28
    MOVQ XMM0, RAX  ; Move to XMM0
    POR xmm15, XMM0  ; OR into packed register
    ; Pack flag_1bit at bit 36, width 1 bits
    MOVZX RAX, BYTE [GLOBAL_flag_1bit]  ; Load flag_1bit
    ; Extract and mask to 1 bits
    AND RAX, 1  ; Mask to 1 bits
    SHL RAX, 36  ; Shift to bit position 36
    MOVQ XMM0, RAX  ; Move to XMM0
    POR xmm15, XMM0  ; OR into packed register
    ; Pack counter_2bit at bit 37, width 2 bits
    MOVZX RAX, BYTE [GLOBAL_counter_2bit]  ; Load counter_2bit
    ; Extract and mask to 2 bits
    AND RAX, 3  ; Mask to 2 bits
    SHL RAX, 37  ; Shift to bit position 37
    MOVQ XMM0, RAX  ; Move to XMM0
    POR xmm15, XMM0  ; OR into packed register
    ; Pack state_3bit at bit 39, width 3 bits
    MOVZX RAX, BYTE [GLOBAL_state_3bit]  ; Load state_3bit
    ; Extract and mask to 3 bits
    AND RAX, 7  ; Mask to 3 bits
    SHL RAX, 39  ; Shift to bit position 39
    MOVQ XMM0, RAX  ; Move to XMM0
    POR xmm15, XMM0  ; OR into packed register
    ; Pack flag_1bit at bit 42, width 1 bits
    MOVZX RAX, BYTE [GLOBAL_flag_1bit]  ; Load flag_1bit
    ; Extract and mask to 1 bits
    AND RAX, 1  ; Mask to 1 bits
    SHL RAX, 42  ; Shift to bit position 42
    MOVQ XMM0, RAX  ; Move to XMM0
    POR xmm15, XMM0  ; OR into packed register
    ; Pack counter_2bit at bit 43, width 2 bits
    MOVZX RAX, BYTE [GLOBAL_counter_2bit]  ; Load counter_2bit
    ; Extract and mask to 2 bits
    AND RAX, 3  ; Mask to 2 bits
    SHL RAX, 43  ; Shift to bit position 43
    MOVQ XMM0, RAX  ; Move to XMM0
    POR xmm15, XMM0  ; OR into packed register
    ; Pack state_3bit at bit 45, width 3 bits
    MOVZX RAX, BYTE [GLOBAL_state_3bit]  ; Load state_3bit
    ; Extract and mask to 3 bits
    AND RAX, 7  ; Mask to 3 bits
    SHL RAX, 45  ; Shift to bit position 45
    MOVQ XMM0, RAX  ; Move to XMM0
    POR xmm15, XMM0  ; OR into packed register
    ; Pack mode_4bit at bit 48, width 4 bits
    MOVZX RAX, BYTE [GLOBAL_mode_4bit]  ; Load mode_4bit
    ; Extract and mask to 4 bits
    AND RAX, 15  ; Mask to 4 bits
    SHL RAX, 48  ; Shift to bit position 48
    MOVQ XMM0, RAX  ; Move to XMM0
    POR xmm15, XMM0  ; OR into packed register
    ; Pack level_5bit at bit 52, width 5 bits
    MOVZX RAX, BYTE [GLOBAL_level_5bit]  ; Load level_5bit
    ; Extract and mask to 5 bits
    AND RAX, 31  ; Mask to 5 bits
    SHL RAX, 52  ; Shift to bit position 52
    MOVQ XMM0, RAX  ; Move to XMM0
    POR xmm15, XMM0  ; OR into packed register
    ; Pack index_6bit at bit 57, width 6 bits
    MOVZX RAX, BYTE [GLOBAL_index_6bit]  ; Load index_6bit
    ; Extract and mask to 6 bits
    AND RAX, 63  ; Mask to 6 bits
    SHL RAX, 57  ; Shift to bit position 57
    MOVQ XMM0, RAX  ; Move to XMM0
    POR xmm15, XMM0  ; OR into packed register
    ; Pack offset_7bit at bit 63, width 7 bits
    MOVZX RAX, BYTE [GLOBAL_offset_7bit]  ; Load offset_7bit
    ; Extract and mask to 7 bits
    AND RAX, 127  ; Mask to 7 bits
    SHL RAX, 63  ; Shift to bit position 63
    MOVQ XMM0, RAX  ; Move to XMM0
    POR xmm15, XMM0  ; OR into packed register
    ; Pack value_8bit at bit 70, width 8 bits
    MOVZX RAX, BYTE [GLOBAL_value_8bit]  ; Load value_8bit
    ; Extract and mask to 8 bits
    AND RAX, 255  ; Mask to 8 bits
    SHL RAX, 70  ; Shift to bit position 70
    MOVQ XMM0, RAX  ; Move to XMM0
    POR xmm15, XMM0  ; OR into packed register
    ; xmm15 now contains all packed global variables
    RET


ALIGN 16
FUNC_main:
    PUSH RBX  ; Callee-saved: preserve RBX
    PUSH RBP  ; Save old frame pointer
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    SUB RSP, 8  ; Adjust for 16-byte stack alignment
    MOV RBP, RSP  ; Set new frame pointer
    MOV R12, 0x7FFF0000  ; Load stack base (immediate)
    XOR R13, R13  ; Initialize slot index to 0
    SUB RSP, 552  ; Allocate stack for all locals
    MOV RAX, 10
    MOV R9D, EAX  ; Initialize local_a in register R9 (32-bit)
    MOV RAX, 20
    MOV R10D, EAX  ; Initialize local_b in register R10 (32-bit)
    MOV RAX, 0
    MOV R11D, EAX  ; Initialize local_c in register R11 (32-bit)
    MOV RAX, 100
    MOV EAX, R9D  ; Load local_a from register R9 (32-bit)
    MOV RDI, RAX
    MOV EAX, R10D  ; Load local_b from register R10 (32-bit)
    MOV RSI, RAX
    ; Single call to add (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 38  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_10:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 10 (stored in single byte)
    MOV R11D, EAX  ; Store local_c to register R11 (32-bit)
    MOV RDI, RAX
    MOV EAX, R11D  ; Load local_c from register R11 (32-bit)
    MOV RSI, RAX
    ; Single call to subtract (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 39  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_11:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 11 (stored in single byte)
    MOV RAX, 5
    MOV RDI, RAX
    MOV RAX, 6
    MOV RSI, RAX
    ; Single call to multiply (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 40  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_12:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 12 (stored in single byte)
    MOV DWORD [RBP - 40], EAX  ; Store result1 (32-bit)
    MOV RAX, 100
    MOV RDI, RAX
    MOV RAX, 4
    MOV RSI, RAX
    ; Single call to divide (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 41  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    MOV DWORD [RBP - 48], EAX  ; Store result2 (32-bit)
    MOV EAX, DWORD [RBP - 40]  ; Load result1 (32-bit)
    MOV RDI, RAX
    MOV EAX, DWORD [RBP - 48]  ; Load result2 (32-bit)
    MOV RSI, RAX
    ; Single call to compare_values (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 42  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    MOV DWORD [RBP - 56], EAX  ; Store cmp1 (32-bit)
    MOV EAX, R9D  ; Load local_a from register R9 (32-bit)
    MOV RDI, RAX
    MOV EAX, R10D  ; Load local_b from register R10 (32-bit)
    MOV RSI, RAX
    ; Single call to compare_values (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 42  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    MOV DWORD [RBP - 64], EAX  ; Store cmp2 (32-bit)
    MOV EAX, DWORD [RBP - 56]  ; Load cmp1 (32-bit)
    PUSH R10  ; Save local_b
    MOV R10, RAX  ; Save left operand
    MOV RAX, 1
    CMP RAX, R10
    SETE AL
    MOVZX RAX, AL
    POP R10  ; Restore temp
    TEST RAX, RAX
    JZ ELSE_4440
    MOV EAX, R9D  ; Load local_a from register R9 (32-bit)
    ADD RAX, 10
    MOV R9D, EAX  ; Store local_a to register R9 (32-bit)
    JMP END_IF_4440
ELSE_4440:
    MOV EAX, DWORD [RBP - 56]  ; Load cmp1 (32-bit)
    PUSH R10  ; Save local_b
    MOV R10, RAX  ; Save left operand
    MOV RAX, 0
    CMP RAX, R10
    SETNE AL
    MOVZX RAX, AL
    POP R10  ; Restore temp
    TEST RAX, RAX
    JZ ELSE_4455
    MOV EAX, R10D  ; Load local_b from register R10 (32-bit)
    ADD RAX, 20
    MOV R10D, EAX  ; Store local_b to register R10 (32-bit)
    JMP END_IF_4455
ELSE_4455:
END_IF_4455:
END_IF_4440:
    PUSH R10  ; Save local_b
    MOV R10, R9  ; Use local_a from register
    MOV EAX, R10D  ; Load local_b from register R10 (32-bit)
    CMP RAX, R10
    SETG AL
    MOVZX RAX, AL
    POP R10  ; Restore temp
    MOV DWORD [RBP - 72], EAX  ; Store gt_test (32-bit)
    PUSH R10  ; Save local_b
    MOV R10, R9  ; Use local_a from register
    MOV EAX, R10D  ; Load local_b from register R10 (32-bit)
    CMP RAX, R10
    SETGE AL
    MOVZX RAX, AL
    POP R10  ; Restore temp
    MOV DWORD [RBP - 80], EAX  ; Store ge_test (32-bit)
    PUSH R10  ; Save local_b
    MOV R10, R9  ; Use local_a from register
    MOV EAX, R10D  ; Load local_b from register R10 (32-bit)
    CMP R10, RAX
    SETLE AL
    MOVZX RAX, AL
    POP R10  ; Restore temp
    MOV DWORD [RBP - 88], EAX  ; Store le_test (32-bit)
    MOV RAX, 0
    MOV R8D, EAX  ; Initialize counter in register R8 (32-bit)
WHILE_4498:
    PUSH R10  ; Save local_b
    MOV R10, R8  ; Use counter from register
    MOV RAX, 5
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    POP R10  ; Restore temp
    TEST RAX, RAX
    JZ END_WHILE_4498
    MOV EAX, R8D  ; Load counter from register R8 (32-bit)
    ADD RAX, 1
    MOV R8D, EAX  ; Store counter to register R8 (32-bit)
    PUSH R10  ; Save local_b
    MOV R10, R11  ; Use local_c from register
    MOV EAX, R8D  ; Load counter from register R8 (32-bit)
    ADD RAX, R10
    POP R10  ; Restore temp
    MOV R11D, EAX  ; Store local_c to register R11 (32-bit)
    JMP WHILE_4498
END_WHILE_4498:
    MOV RAX, 0
    MOV DWORD [RBP - 104], EAX  ; Store sum (32-bit)
    MOV RAX, 0
    MOV EBX, EAX  ; Initialize i in register RBX (32-bit)
FOR_4521:
    PUSH R10  ; Save local_b
    MOV R10, RBX  ; Use i from register
    MOV RAX, 10
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    POP R10  ; Restore temp
    TEST RAX, RAX
    JZ END_FOR_4521
    MOV EAX, DWORD [RBP - 104]  ; Load sum (32-bit)
    PUSH R10  ; Save local_b
    MOV R10, RAX  ; Save left operand
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    ADD RAX, R10
    POP R10  ; Restore temp
    MOV DWORD [RBP - 104], EAX  ; Store sum (32-bit)
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    ADD RAX, 1
    MOV EBX, EAX  ; Store i to register RBX (32-bit)
    JMP FOR_4521
END_FOR_4521:
    XOR RAX, RAX  ; Initialize global_array to 0
    MOV DWORD [RBP - 152], EAX  ; Store global_array (32-bit)
    MOV RAX, 0
    MOV EBX, EAX  ; Reinit i in register RBX
FOR_4547:
    PUSH R10  ; Save local_b
    MOV R10, RBX  ; Use i from register
    MOV RAX, 10
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    POP R10  ; Restore temp
    TEST RAX, RAX
    JZ END_FOR_4547
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    ADD RAX, RAX
    PUSH RAX  ; Save value to assign
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    PUSH RAX  ; Save index
    LEA RBX, [rel GLOBAL_global_array]  ; Base address of array (PIC)
    POP RAX  ; Get index
    ; Array assignment: base + index * 4
    LEA RAX, [RBX + RAX*4]  ; base + index*4
    POP RCX  ; Get value to assign
    MOV DWORD [RAX], ECX  ; Store to array element
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    ADD RAX, 1
    MOV EBX, EAX  ; Store i to register RBX (32-bit)
    JMP FOR_4547
END_FOR_4547:
    MOV RAX, 0
    MOV DWORD [RBP - 160], EAX  ; Store arr_sum (32-bit)
    MOV RAX, 0
    MOV EBX, EAX  ; Reinit i in register RBX
FOR_4577:
    PUSH R10  ; Save local_b
    MOV R10, RBX  ; Use i from register
    MOV RAX, 10
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    POP R10  ; Restore temp
    TEST RAX, RAX
    JZ END_FOR_4577
    MOV EAX, DWORD [RBP - 160]  ; Load arr_sum (32-bit)
    PUSH R10  ; Save local_b
    MOV R10, RAX  ; Save left operand
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    MOV RCX, RAX  ; Save index
    LEA RAX, [rel GLOBAL_global_array + RCX*4]  ; Base + index*4 (int is 4 bytes, PIC)
    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)
    ADD RAX, R10
    POP R10  ; Restore temp
    MOV DWORD [RBP - 160], EAX  ; Store arr_sum (32-bit)
    MOV EAX, EBX  ; Load i from register RBX (32-bit)
    ADD RAX, 1
    MOV EBX, EAX  ; Store i to register RBX (32-bit)
    JMP FOR_4577
END_FOR_4577:
    PUSH R10  ; Save local_b
    MOV R10, R9  ; Use local_a from register
    MOV RAX, 7
    ; Modulo operation: R10 % RAX
    PUSH RAX  ; Save right operand (divisor)
    MOV RAX, R10  ; Move left operand (dividend) to RAX
    POP R10  ; Get divisor
    XOR RDX, RDX  ; Clear RDX for division
    DIV R10  ; RAX = dividend / divisor, RDX = remainder
    MOV RAX, RDX  ; Remainder is the modulo result
    POP R10  ; Restore temp
    MOV DWORD [RBP - 168], EAX  ; Store mod_result (32-bit)
    PUSH R10  ; Save local_b
    MOV R10, R9  ; Use local_a from register
    MOV RAX, 0
    CMP RAX, R10
    SETG AL
    MOVZX RAX, AL
    POP R10  ; Restore temp
    PUSH R10  ; Save local_b
    MOV R10, RAX  ; Save left operand
    MOV R10, R10  ; Use local_b from register
    MOV RAX, 0
    CMP RAX, R10
    SETG AL
    MOVZX RAX, AL
    ; Logical AND: R10 && RAX
    TEST R10, R10  ; Check if left is non-zero
    JZ AND_FALSE_14
    TEST RAX, RAX  ; Check if right is non-zero
    JZ AND_FALSE_14
    MOV RAX, 1  ; Both non-zero, result is 1
    JMP AND_END_14
AND_FALSE_14:
    MOV RAX, 0  ; One or both zero, result is 0
AND_END_14:
    MOV DWORD [RBP - 176], EAX  ; Store and_result (32-bit)
    PUSH R10  ; Save local_b
    MOV R10, R9  ; Use local_a from register
    MOV RAX, 0
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    POP R10  ; Restore temp
    PUSH R10  ; Save local_b
    MOV R10, RAX  ; Save left operand
    MOV R10, R10  ; Use local_b from register
    MOV RAX, 0
    CMP R10, RAX
    SETL AL
    MOVZX RAX, AL
    ; Logical OR: R10 || RAX
    TEST R10, R10  ; Check if left is non-zero
    JNZ OR_TRUE_15
    TEST RAX, RAX  ; Check if right is non-zero
    JNZ OR_TRUE_15
    MOV RAX, 0  ; Both zero, result is 0
    JMP OR_END_15
OR_TRUE_15:
    MOV RAX, 1  ; At least one non-zero, result is 1
OR_END_15:
    MOV DWORD [RBP - 184], EAX  ; Store or_result (32-bit)
    PUSH R10  ; Save local_b
    MOV R10, R9  ; Use local_a from register
    MOV RAX, 2
    ; Left shift: R10 << RAX
    MOV RCX, RAX  ; Shift amount in RCX
    MOV RAX, R10  ; Value to shift
    SHL RAX, CL  ; Left shift by CL (low 8 bits of RCX)
    POP R10  ; Restore temp
    MOV DWORD [RBP - 192], EAX  ; Store shift_left (32-bit)
    MOV R10, R10  ; Use local_b from register
    MOV RAX, 1
    ; Right shift: R10 >> RAX
    MOV RCX, RAX  ; Shift amount in RCX
    MOV RAX, R10  ; Value to shift
    SHR RAX, CL  ; Right shift by CL (low 8 bits of RCX)
    MOV DWORD [RBP - 200], EAX  ; Store shift_right (32-bit)
    MOV RAX, 10
    MOV RDI, RAX
    MOV RAX, 3
    MOV RSI, RAX
    ; Single call to left_shift (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 9  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_13:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 13 (stored in single byte)
    PUSH R10  ; Save local_b
    MOV R10, RAX  ; Save left operand
    MOV RAX, 100
    MOV RDI, RAX
    MOV RAX, 2
    MOV RSI, RAX
    ; Single call to right_shift (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 10  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_14:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 14 (stored in single byte)
    ADD RAX, R10
    POP R10  ; Restore temp
    MOV DWORD [RBP - 208], EAX  ; Store shift_result (32-bit)
    PUSH R10  ; Save local_b
    MOV R10, R9  ; Use local_a from register
    MOV EAX, R10D  ; Load local_b from register R10 (32-bit)
    ; Bitwise AND: R10 & RAX
    AND RAX, R10
    POP R10  ; Restore temp
    MOV DWORD [RBP - 216], EAX  ; Store bit_and (32-bit)
    PUSH R10  ; Save local_b
    MOV R10, R9  ; Use local_a from register
    MOV EAX, R10D  ; Load local_b from register R10 (32-bit)
    ; Bitwise OR: R10 | RAX
    OR RAX, R10
    POP R10  ; Restore temp
    MOV DWORD [RBP - 224], EAX  ; Store bit_or (32-bit)
    PUSH R10  ; Save local_b
    MOV R10, R9  ; Use local_a from register
    MOV EAX, R10D  ; Load local_b from register R10 (32-bit)
    ; Bitwise XOR: R10 ^ RAX
    XOR RAX, R10
    POP R10  ; Restore temp
    MOV DWORD [RBP - 232], EAX  ; Store bit_xor (32-bit)
    MOV EAX, R9D  ; Load local_a from register R9 (32-bit)
    ; Bitwise NOT: ~expr
    NOT RAX
    MOV DWORD [RBP - 240], EAX  ; Store bit_not (32-bit)
    MOV RAX, 5
    MOV RDI, RAX
    MOV RAX, 3
    MOV RSI, RAX
    ; Single call to bitwise_and (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 11  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_15:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 15 (stored in single byte)
    PUSH R10  ; Save local_b
    MOV R10, RAX  ; Save left operand
    MOV RAX, 5
    MOV RDI, RAX
    MOV RAX, 3
    MOV RSI, RAX
    ; Single call to bitwise_or (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 12  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_16:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 16 (stored in single byte)
    ADD RAX, R10
    POP R10  ; Restore temp
    PUSH R10  ; Save local_b
    MOV R10, RAX  ; Save left operand
    MOV RAX, 5
    MOV RDI, RAX
    MOV RAX, 3
    MOV RSI, RAX
    ; Single call to bitwise_xor (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 13  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_17:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 17 (stored in single byte)
    ADD RAX, R10
    POP R10  ; Restore temp
    PUSH R10  ; Save local_b
    MOV R10, RAX  ; Save left operand
    MOV RAX, 5
    MOV RDI, RAX
    ; Single call to bitwise_not (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 14  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_18:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 18 (stored in single byte)
    ADD RAX, R10
    POP R10  ; Restore temp
    MOV DWORD [RBP - 248], EAX  ; Store bitwise_result (32-bit)
    MOV EAX, R9D  ; Load local_a from register R9 (32-bit)
    MOV RDI, RAX
    MOV EAX, R10D  ; Load local_b from register R10 (32-bit)
    MOV RSI, RAX
    ; Single call to test_compound_bitwise (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 21  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_19:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 19 (stored in single byte)
    MOV DWORD [RBP - 256], EAX  ; Store compound_bitwise (32-bit)
    MOV RAX, 5
    MOV RDI, RAX
    ; Single call to power_of_2 (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 16  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    MOV DWORD [RBP - 264], EAX  ; Store pow2 (32-bit)
    ; Single call to test_struct_operations (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 67  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_20:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 20 (stored in single byte)
    MOV DWORD [RBP - 272], EAX  ; Store struct_result (32-bit)
    MOV EAX, R9D  ; Load local_a from register R9 (32-bit)
    MOV RDI, RAX
    MOV EAX, R10D  ; Load local_b from register R10 (32-bit)
    MOV RSI, RAX
    ; Single call to test_compound_assignment (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 48  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_21:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 21 (stored in single byte)
    MOV DWORD [RBP - 280], EAX  ; Store compound_result (32-bit)
    MOV EAX, R9D  ; Load local_a from register R9 (32-bit)
    MOV RDI, RAX
    ; Single call to test_increment_decrement (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 49  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_22:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 22 (stored in single byte)
    MOV DWORD [RBP - 288], EAX  ; Store inc_dec_result (32-bit)
    MOV EAX, R9D  ; Load local_a from register R9 (32-bit)
    MOV RDI, RAX
    MOV EAX, R10D  ; Load local_b from register R10 (32-bit)
    MOV RSI, RAX
    ; Single call to test_ternary (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 50  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_23:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 23 (stored in single byte)
    MOV DWORD [RBP - 296], EAX  ; Store ternary_result (32-bit)
    PUSH R10  ; Save local_b
    MOV R10, R9  ; Use local_a from register
    MOV EAX, R10D  ; Load local_b from register R10 (32-bit)
    CMP RAX, R10
    SETG AL
    MOVZX RAX, AL
    POP R10  ; Restore temp
    TEST RAX, RAX  ; Check condition
    JZ TERNARY_FALSE_16
    MOV EAX, R9D  ; Load local_a from register R9 (32-bit)
    JMP TERNARY_END_16
TERNARY_FALSE_16:
    MOV EAX, R10D  ; Load local_b from register R10 (32-bit)
TERNARY_END_16:
    MOV DWORD [RBP - 304], EAX  ; Store ternary_direct (32-bit)
    MOV EAX, R9D  ; Load local_a from register R9 (32-bit)
    MOV RDI, RAX
    MOV EAX, R10D  ; Load local_b from register R10 (32-bit)
    MOV RSI, RAX
    ; Single call to test_combined_operators (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 53  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_24:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 24 (stored in single byte)
    MOV DWORD [RBP - 312], EAX  ; Store combined_result (32-bit)
    MOV EAX, R9D  ; Load local_a from register R9 (32-bit)
    MOV EAX, R9D  ; Load local_a from register R9 (32-bit)
    INC RAX
    MOV DWORD [RBP - 8], EAX  ; Store local_a
    MOV DWORD [RBP - 320], EAX  ; Store pre_inc (32-bit)
    MOV EAX, R10D  ; Load local_b from register R10 (32-bit)
    MOV EAX, R10D  ; Load local_b from register R10 (32-bit)
    PUSH RAX  ; Save original value
    INC RAX
    MOV DWORD [RBP - 16], EAX  ; Store local_b
    MOV R10D, EAX  ; Update local_b in register R10 (32-bit)
    POP RAX  ; Return original value
    MOV DWORD [RBP - 328], EAX  ; Store post_inc (32-bit)
    MOV EAX, R9D  ; Load local_a from register R9 (32-bit)
    MOV EAX, R9D  ; Load local_a from register R9 (32-bit)
    DEC RAX
    MOV DWORD [RBP - 8], EAX  ; Store local_a
    MOV DWORD [RBP - 336], EAX  ; Store pre_dec (32-bit)
    MOV EAX, R10D  ; Load local_b from register R10 (32-bit)
    MOV EAX, R10D  ; Load local_b from register R10 (32-bit)
    PUSH RAX  ; Save original value
    DEC RAX
    MOV DWORD [RBP - 16], EAX  ; Store local_b
    MOV R10D, EAX  ; Update local_b in register R10 (32-bit)
    POP RAX  ; Return original value
    MOV DWORD [RBP - 344], EAX  ; Store post_dec (32-bit)
    MOV EAX, R9D  ; Load local_a from register R9 (32-bit)
    PUSH RAX  ; Save current value
    MOV RAX, 10
    POP R10  ; Get current value
    ADD RAX, R10
    MOV R9D, EAX  ; Store local_a to register R9 (32-bit)
    MOV EAX, R10D  ; Load local_b from register R10 (32-bit)
    PUSH RAX  ; Save current value
    MOV RAX, 5
    POP R10  ; Get current value
    SUB R10, RAX
    MOV RAX, R10
    MOV R10D, EAX  ; Store local_b to register R10 (32-bit)
    MOV EAX, R11D  ; Load local_c from register R11 (32-bit)
    PUSH RAX  ; Save current value
    MOV RAX, 2
    POP R10  ; Get current value
    MUL R10
    MOV R11D, EAX  ; Store local_c to register R11 (32-bit)
    PUSH RAX  ; Save current value
    MOV RAX, 2
    POP R10  ; Get current value
    MOV RCX, RAX  ; Save divisor
    MOV RAX, R10  ; Dividend
    XOR RDX, RDX
    DIV RCX
    MOV EAX, R9D  ; Load local_a from register R9 (32-bit)
    MOV DWORD [RBP - 352], EAX  ; Store mod_temp (32-bit)
    MOV EAX, DWORD [RBP - 352]  ; Load mod_temp (32-bit)
    PUSH RAX  ; Save current value
    MOV RAX, 7
    POP R10  ; Get current value
    MOV RCX, RAX  ; Save divisor
    MOV RAX, R10  ; Dividend
    XOR RDX, RDX
    DIV RCX
    MOV RAX, RDX  ; Remainder
    MOV DWORD [RBP - 352], EAX  ; Store mod_temp (32-bit)
    MOV RAX, 5
    MOV RDI, RAX
    ; Single call to factorial (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 22  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_25:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 25 (stored in single byte)
    MOV DWORD [RBP - 360], EAX  ; Store fact_result (32-bit)
    MOV RAX, 7
    MOV RDI, RAX
    ; Single call to fibonacci (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 23  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    MOV DWORD [RBP - 368], EAX  ; Store fib_result (32-bit)
    MOV RAX, [GLOBAL_global_counter]  ; Load global variable
    ADD RAX, 1
    MOV [GLOBAL_global_counter], RAX
    MOV EAX, DWORD [RBP - 360]  ; Load fact_result (32-bit)
    PUSH R10  ; Save local_b
    MOV R10, RAX  ; Save left operand
    MOV EAX, DWORD [RBP - 368]  ; Load fib_result (32-bit)
    ADD RAX, R10
    POP R10  ; Restore temp
    MOV [GLOBAL_global_result], RAX
    MOV RAX, 1
    MOV BYTE [GLOBAL_flag_1bit], AL  ; Store to packed variable
    MOV RAX, 3
    MOV BYTE [GLOBAL_counter_2bit], AL  ; Store to packed variable
    MOV RAX, 5
    MOV BYTE [GLOBAL_state_3bit], AL  ; Store to packed variable
    MOV RAX, 10
    MOV BYTE [GLOBAL_mode_4bit], AL  ; Store to packed variable
    MOV RAX, 15
    MOV BYTE [GLOBAL_level_5bit], AL  ; Store to packed variable
    MOV RAX, 20
    MOV BYTE [GLOBAL_index_6bit], AL  ; Store to packed variable
    MOV RAX, 30
    MOV BYTE [GLOBAL_offset_7bit], AL  ; Store to packed variable
    MOV RAX, 50
    MOV BYTE [GLOBAL_value_8bit], AL  ; Store to packed variable
    MOVZX EAX, BYTE [GLOBAL_flag_1bit]  ; Load packed variable
    MOV DWORD [RBP - 376], EAX  ; Store read_flag (32-bit)
    MOVZX EAX, BYTE [GLOBAL_counter_2bit]  ; Load packed variable
    MOV DWORD [RBP - 384], EAX  ; Store read_counter (32-bit)
    MOVZX EAX, BYTE [GLOBAL_state_3bit]  ; Load packed variable
    MOV DWORD [RBP - 392], EAX  ; Store read_state (32-bit)
    MOV EAX, R9D  ; Load local_a from register R9 (32-bit)
    NEG RAX
    MOV DWORD [RBP - 400], EAX  ; Store neg_value (32-bit)
    MOV EAX, DWORD [RBP - 56]  ; Load cmp1 (32-bit)
    NOT RAX
    MOV DWORD [RBP - 408], EAX  ; Store not_value (32-bit)
    PUSH R10  ; Save local_b
    MOV R10, R9  ; Use local_a from register
    MOV EAX, R10D  ; Load local_b from register R10 (32-bit)
    ADD RAX, R10
    POP R10  ; Restore temp
    PUSH R10  ; Save local_b
    MOV R10, RAX  ; Save left operand
    PUSH R10  ; Save local_b
    MOV R10, R11  ; Use local_c from register
    SUB R10, RAX
    MOV RAX, R10
    POP R10  ; Restore temp
    MUL R10
    PUSH R10  ; Save local_b
    MOV R10, RAX  ; Save left operand
    MOV RAX, 2
    MOV RCX, RAX  ; Save divisor
    MOV RAX, R10  ; Dividend to RAX
    XOR RDX, RDX  ; Clear RDX for unsigned division
    DIV RCX  ; RAX = RAX / RCX
    POP R10  ; Restore temp
    MOV DWORD [RBP - 416], EAX  ; Store complex (32-bit)
    MOV RAX, 2
    MOV RDI, RAX
    MOV RAX, 3
    MOV RSI, RAX
    ; Single call to multiply (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 40  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_26:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 26 (stored in single byte)
    MOV RDI, RAX
    MOV RAX, 10
    MOV RDI, RAX
    MOV RAX, 5
    MOV RSI, RAX
    ; Single call to subtract (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 39  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_27:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 27 (stored in single byte)
    MOV RSI, RAX
    ; Single call to add (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 38  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_28:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 28 (stored in single byte)
    MOV DWORD [RBP - 424], EAX  ; Store nested (32-bit)
    LEA RAX, [RBP - 152]  ; Array address
    MOV RDI, RAX
    MOV RAX, 10
    MOV RSI, RAX
    ; Single call to sum_array_elements (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 0  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_29:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 29 (stored in single byte)
    MOV DWORD [RBP - 432], EAX  ; Store arr_sum_func (32-bit)
    LEA RAX, [RBP - 152]  ; Array address
    MOV RDI, RAX
    MOV RAX, 10
    MOV RSI, RAX
    ; Single call to find_max (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 1  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    MOV DWORD [RBP - 440], EAX  ; Store arr_max (32-bit)
    LEA RAX, [RBP - 152]  ; Array address
    MOV RDI, RAX
    MOV RAX, 10
    MOV RSI, RAX
    ; Single call to find_min (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 2  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    MOV DWORD [RBP - 448], EAX  ; Store arr_min (32-bit)
    LEA RAX, [RBP - 152]  ; Array address
    MOV RDI, RAX
    MOV RAX, 10
    MOV RSI, RAX
    ; Single call to reverse_array (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 3  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_30:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 30 (stored in single byte)
    LEA RAX, [RBP - 152]  ; Array address
    MOV RDI, RAX
    MOV RAX, 10
    MOV RSI, RAX
    ; Single call to test_array_modulo (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 6  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_31:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 31 (stored in single byte)
    MOV DWORD [RBP - 456], EAX  ; Store arr_mod (32-bit)
    LEA RAX, [RBP - 152]  ; Array address
    MOV RDI, RAX
    MOV RAX, 10
    MOV RSI, RAX
    ; Single call to test_array_comparisons (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 7  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_32:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 32 (stored in single byte)
    MOV DWORD [RBP - 464], EAX  ; Store arr_cmp (32-bit)
    LEA RAX, [RBP - 152]  ; Array address
    MOV RDI, RAX
    MOV RAX, 10
    MOV RSI, RAX
    ; Single call to test_array_logical (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 8  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_33:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 33 (stored in single byte)
    MOV DWORD [RBP - 472], EAX  ; Store arr_log (32-bit)
    ; Single call to isr_timer_handler (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 34  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_34:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 34 (stored in single byte)
    MOV DWORD [RBP - 480], EAX  ; Store timer_result (32-bit)
    ; Single call to irq_keyboard_handler (SMALL_FUNC_BASE + index*1024)
    MOV RAX, SMALL_FUNC_BASE
    MOV R11, 35  ; Function index
    SHL R11, 10  ; index * 1024
    ADD RAX, R11
    CALL RAX  ; One call only
    ALIGN 16
RET_SITE_main_35:  ; Quantized call-back (16-byte aligned)
    ; Return site offset: 35 (stored in single byte)
    MOV DWORD [RBP - 488], EAX  ; Store keyboard_result (32-bit)
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    ADD RSP, 8  ; Restore RSP alignment adjustment
    POP R13  ; Restore stack index register
    POP R12  ; Restore stack base register
    POP RBP
    POP RBX  ; Restore callee-saved RBX
FUNC_main_METAMORPHIC:
    MOV RDX, 0xdeadbeef  ; Metamorphic return address (will be overwritten by caller)
    JMP RDX  ; Jump to return address

SECTION .data

STACK_BASE:
    DQ 0x7FFF0000  ; Stack base address

GLOBAL_global_array:
    TIMES 10 DD 0  ; global_array[10]
GLOBAL_global_counter:
    DD 0  ; global_counter
GLOBAL_global_result:
    DD 0  ; global_result
GLOBAL_global_sum:
    DD 0  ; global_sum
GLOBAL_global_max:
    DD 0  ; global_max
GLOBAL_global_min:
    DD 0  ; global_min (string constant)
GLOBAL_flag_1bit:
    DB 0  ; flag_1bit (packed into SIMD register)
GLOBAL_counter_2bit:
    DB 0  ; counter_2bit (packed into SIMD register)
GLOBAL_state_3bit:
    DB 0  ; state_3bit (packed into SIMD register)
GLOBAL_mode_4bit:
    DB 0  ; mode_4bit (packed into SIMD register)
GLOBAL_level_5bit:
    DB 0  ; level_5bit (packed into SIMD register)
GLOBAL_index_6bit:
    DB 0  ; index_6bit (packed into SIMD register)
GLOBAL_offset_7bit:
    DB 0  ; offset_7bit (packed into SIMD register)
GLOBAL_value_8bit:
    DB 0  ; value_8bit (packed into SIMD register)
GLOBAL_a:
    DD 0  ; a
GLOBAL_b:
    DD 0  ; b
GLOBAL_n:
    DD 0  ; n
GLOBAL_data:
    DD 0  ; data
GLOBAL_len:
    DD 0  ; len
GLOBAL_arr:
    DD 0  ; arr
GLOBAL_value:
    DD 0  ; value
GLOBAL_shift:
    DD 0  ; shift
GLOBAL_x:
    DD 0  ; x
GLOBAL_y:
    DD 0  ; y
GLOBAL_width:
    DD 0  ; width
GLOBAL_height:
    DD 0  ; height
GLOBAL_global_point:
    TIMES 8 DB 0  ; global_point (struct)
