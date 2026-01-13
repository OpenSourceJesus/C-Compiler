# Testing the Indexed Stack Pointer System

This guide explains how to test the indexed stack pointer implementation that uses 16-byte intervals for pointer compression.

## Prerequisites

1. Install dependencies:
```bash
pip3 install -r requirements.txt
```

2. Ensure Python 3 is available

## Quick Test

Run the automated test script:
```bash
./test_indexed_stack.sh
```

Or manually compile and inspect:
```bash
python3 compiler.py test_indexed_stack.c -o test_indexed_stack.asm -v
```

## What to Look For

### 1. Stack Base Initialization

In the `.data` section, you should see:
```asm
STACK_BASE:
    DQ 0x7FFF0000  ; Stack base address
```

### 2. Function Prologue

Each function should initialize the indexed stack pointer:
```asm
FUNC_test_local_vars:
    ; Indexed stack pointer prologue (16-byte intervals)
    PUSH RBP
    PUSH R12  ; Preserve stack base register
    PUSH R13  ; Preserve stack index register
    MOV RBP, RSP  ; Save old RSP
    
    ; Initialize indexed stack pointer system
    MOV R12, STACK_BASE  ; Load stack base
    XOR R13, R13  ; Initialize slot index to 0
```

### 3. Local Variable Allocation

Variables should be allocated in 16-byte slots:
```asm
    ; Allocate slot 0 (16 bytes) for a
    INC R13  ; Increment slot index
```

### 4. Variable Access

Variables should be accessed using indexed addressing:
```asm
    ; Load local variable a from slot 0, offset 0
    ; Indexed stack: address = [R12 + 0*16 + 0]
    MOV RAX, [R12]  ; Load from slot 0
```

Or for later slots:
```asm
    ; Load local variable c from slot 2, offset 0
    ; Indexed stack: address = [R12 + 2*16 + 0]
    MOV RAX, [R12 + 32]  ; Load from slot 2
```

### 5. Function Epilogue

Should restore registers and reset stack index:
```asm
    XOR R13, R13  ; Reset stack index
    MOV RSP, RBP
    POP RBP
    RET
```

## Manual Verification Checklist

- [ ] `STACK_BASE` is defined in `.data` section
- [ ] Function prologues initialize `R12` (stack base) and `R13` (index)
- [ ] Local variables are allocated using `INC R13` (slot allocation)
- [ ] Variable access uses `[R12 + displacement]` pattern
- [ ] Displacements are multiples of 16 (0, 16, 32, 48, etc.)
- [ ] Comments mention "Indexed stack" and "pointer compression"
- [ ] Function epilogues reset `R13` to 0

## Testing Different Scenarios

### Test 1: Simple Local Variables
```c
int test() {
    int a = 10;
    int b = 20;
    return a + b;
}
```
**Expected**: Two slots allocated (slot 0 and slot 1), accessed via `[R12]` and `[R12 + 16]`

### Test 2: Multiple Operations
```c
int test(int x) {
    int a = x * 2;
    int b = a + 5;
    return b;
}
```
**Expected**: Variables allocated sequentially, operations use indexed addressing

### Test 3: Nested Function Calls
```c
int helper(int x) {
    int local = x + 1;
    return local;
}

int main() {
    int result = helper(10);
    return result;
}
```
**Expected**: Each function maintains its own stack index, properly saved/restored

## Pointer Compression Verification

To verify pointer compression works, look for:
1. **32-bit indices**: Slot indices should fit in 32 bits (values < 2^32)
2. **Compressed pointer function**: The `_generate_compressed_pointer()` method should allow packing two indices

Example of compressed pointer usage:
```asm
    ; Compressed pointer: slot 1 (low) + slot 2 (high)
    MOV EAX, 1   ; Lower 32 bits: slot index 1
    MOV EDX, 2   ; Upper 32 bits: slot index 2
    SHL RDX, 32  ; Shift upper index to high 32 bits
    OR RAX, RDX  ; Combine: RAX = (2 << 32) | 1
```

## Troubleshooting

### Issue: Variables not using indexed addressing
- Check that `_generate_local_var_load()` and `_generate_local_var_store()` are being called
- Verify `current_function_stack` is being populated correctly

### Issue: Stack base not initialized
- Ensure `_generate_data_section()` includes stack base definition
- Check that R12 is loaded with `STACK_BASE` in function prologue

### Issue: Slot indices not incrementing
- Verify `INC R13` is called when allocating variables
- Check that `current_stack_slots` is being tracked correctly

## Expected Output Example

For `test_indexed_stack.c`, you should see output like:

```asm
SECTION .data

; Indexed stack pointer system (16-byte intervals)
STACK_BASE:
    DQ 0x7FFF0000  ; Stack base address

SECTION .text

FUNC_test_local_vars:
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
    MOV [R12], RAX  ; Store to slot 0
    
    ; Allocate slot 1 (16 bytes) for b
    INC R13
    MOV RAX, 20
    MOV [R12 + 16], RAX  ; Store to slot 1
    
    ; ... rest of function
```

## Next Steps

After verifying the basic functionality:
1. Test with larger programs
2. Verify pointer compression with dual-stack scenarios
3. Check performance implications
4. Test edge cases (many variables, nested calls, etc.)
