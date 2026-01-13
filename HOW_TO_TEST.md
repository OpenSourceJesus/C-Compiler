# How to Test the Indexed Stack Pointer System

## Overview

The compiler now uses an **indexed stack pointer system** that references 16-byte intervals instead of a linear byte-addressed stack. This enables pointer compression where 64-bit addresses can be represented as 32-bit indices.

## Quick Start

### 1. Install Dependencies
```bash
pip3 install pycparser pycparser-fake-libc
```

### 2. Run Automated Test
```bash
./test_indexed_stack.sh
```

### 3. Or Compile Manually
```bash
python3 compiler.py test_indexed_stack.c -o test_indexed_stack.asm -v
```

## What Changed

### Before (Linear Stack)
- Variables accessed via: `[RBP - offset]` (byte offsets)
- Stack pointer: `RSP` with byte-level addressing
- No pointer compression possible

### After (Indexed Stack)
- Variables accessed via: `[R12 + slot_index*16]` (16-byte slots)
- Stack base: `R12` contains `STACK_BASE` address
- Stack index: `R13` contains slot index (fits in 32 bits)
- **Pointer compression**: Two 32-bit indices can fit in one 64-bit register

## Verification Checklist

When you compile a test file, verify these in the generated `.asm` file:

### ✅ Stack Base Initialization
```asm
SECTION .data
STACK_BASE:
    DQ 0x7FFF0000  ; Stack base address
```

### ✅ Function Prologue
```asm
FUNC_function_name:
    PUSH RBP
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    MOV RBP, RSP
    MOV R12, STACK_BASE  ; Load stack base
    XOR R13, R13  ; Initialize slot index to 0
```

### ✅ Variable Allocation
```asm
    ; Allocate slot 0 (16 bytes) for variable_name
    INC R13  ; Increment slot index
    MOV [R12], RAX  ; Store to slot 0
```

### ✅ Variable Access
```asm
    ; Load from slot 0: [R12 + 0]
    MOV RAX, [R12]
    
    ; Load from slot 1: [R12 + 16]
    MOV RAX, [R12 + 16]
    
    ; Load from slot 2: [R12 + 32]
    MOV RAX, [R12 + 32]
```

### ✅ Function Epilogue
```asm
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    POP R13
    POP R12
    POP RBP
    RET
```

## Test Files

1. **test_indexed_stack.c** - Comprehensive test with multiple functions and local variables
2. **test.c** - Simple test (can also be used)
3. **test_simd.c** - Tests SIMD features (also uses indexed stack for local vars)

## Manual Verification Commands

```bash
# Check for stack base
grep "STACK_BASE" test_indexed_stack.asm

# Check for R12 usage (should see many)
grep "R12" test_indexed_stack.asm | wc -l

# Check for R13 usage (should see slot management)
grep "R13" test_indexed_stack.asm

# Check for indexed addressing pattern
grep "\[R12" test_indexed_stack.asm

# Check for 16-byte intervals
grep -E "16|slot" test_indexed_stack.asm

# Verify no old-style addressing (should be empty or minimal)
grep "RBP-" test_indexed_stack.asm
```

## Expected Results

### Success Indicators
- ✅ All local variables use `[R12 + displacement]` addressing
- ✅ Displacements are multiples of 16 (0, 16, 32, 48, 64, ...)
- ✅ R13 is incremented for each variable allocation
- ✅ R13 is reset to 0 in function epilogue
- ✅ Comments mention "Indexed stack" and "pointer compression"
- ✅ Stack base is defined in data section

### Failure Indicators
- ❌ Still seeing `[RBP - offset]` for local variables
- ❌ No `STACK_BASE` definition
- ❌ R12/R13 not used in function prologues
- ❌ Displacements not multiples of 16
- ❌ No comments about indexed stack

## Example Test Case

**Input (test_indexed_stack.c):**
```c
int test() {
    int a = 10;
    int b = 20;
    return a + b;
}
```

**Expected Output (excerpt):**
```asm
FUNC_test:
    ; Indexed stack pointer prologue (16-byte intervals)
    PUSH RBP
    PUSH R12
    PUSH R13
    MOV RBP, RSP
    MOV R12, STACK_BASE
    XOR R13, R13
    
    ; Allocate slot 0 (16 bytes) for a
    INC R13
    MOV RAX, 10
    MOV [R12], RAX
    
    ; Allocate slot 1 (16 bytes) for b
    INC R13
    MOV RAX, 20
    MOV [R12 + 16], RAX
    
    ; Load local variable a from slot 0
    MOV RAX, [R12]
    
    ; Load local variable b from slot 1
    MOV RBX, [R12 + 16]
    ADD RAX, RBX
    
    ; Epilogue
    XOR R13, R13
    MOV RSP, RBP
    POP R13
    POP R12
    POP RBP
    RET
```

## Pointer Compression Test

To test pointer compression, look for the ability to pack two indices:

```asm
    ; Compressed pointer: two 32-bit indices in one 64-bit register
    MOV EAX, 1   ; Lower 32 bits: slot index 1
    MOV EDX, 2   ; Upper 32 bits: slot index 2
    SHL RDX, 32
    OR RAX, RDX  ; RAX = (2 << 32) | 1
```

This demonstrates that two stack pointers can be stored in a single 64-bit register.

## Troubleshooting

### Compilation Errors
- **ModuleNotFoundError**: Install dependencies with `pip3 install pycparser pycparser-fake-libc`
- **Parse errors**: Check C syntax in test file
- **Import errors**: Ensure all Python files are in the same directory

### Wrong Output
- **No indexed addressing**: Check that `_generate_local_var_load/store()` are being called
- **Missing STACK_BASE**: Verify `_generate_data_section()` includes stack base
- **R12/R13 not initialized**: Check function prologue generation

## Next Steps

After verifying basic functionality:
1. Test with more complex programs
2. Verify pointer compression in dual-stack scenarios  
3. Test nested function calls
4. Check performance with many local variables
5. Verify 16-byte alignment benefits

## Additional Resources

- `TESTING.md` - Detailed testing procedures
- `QUICK_TEST.md` - Quick reference guide
- `test_indexed_stack.c` - Test file with various scenarios
- `test_indexed_stack.sh` - Automated test script
