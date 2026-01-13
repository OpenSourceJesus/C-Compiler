# Quick Testing Guide for Indexed Stack Pointer

## Step 1: Install Dependencies

```bash
pip3 install pycparser pycparser-fake-libc
```

## Step 2: Compile Test File

```bash
python3 compiler.py test_indexed_stack.c -o test_indexed_stack.asm -v
```

## Step 3: Verify Key Features

Open `test_indexed_stack.asm` and search for these patterns:

### ✅ Must Have Features

1. **Stack Base Definition** (in `.data` section):
   ```
   STACK_BASE:
       DQ 0x7FFF0000
   ```

2. **Function Prologue** (should appear in each function):
   ```
   PUSH R12  ; Preserve stack base register
   PUSH R13  ; Preserve stack index register
   MOV R12, STACK_BASE
   XOR R13, R13
   ```

3. **Slot Allocation** (when declaring variables):
   ```
   INC R13  ; Increment slot index
   ```

4. **Indexed Addressing** (when accessing variables):
   ```
   MOV RAX, [R12 + 0]      ; Slot 0
   MOV RAX, [R12 + 16]     ; Slot 1
   MOV RAX, [R12 + 32]     ; Slot 2
   ```

5. **Comments mentioning**:
   - "Indexed stack"
   - "16-byte intervals"
   - "pointer compression"
   - "32 bits"

## Step 4: Visual Inspection

Use `grep` to quickly check:

```bash
# Check for stack base
grep -i "STACK_BASE" test_indexed_stack.asm

# Check for R12 usage (stack base register)
grep "R12" test_indexed_stack.asm | head -5

# Check for R13 usage (stack index register)
grep "R13" test_indexed_stack.asm | head -5

# Check for indexed addressing
grep "\[R12" test_indexed_stack.asm | head -5

# Check for 16-byte intervals
grep "16\|slot" test_indexed_stack.asm | head -10
```

## Expected Pattern

For a function like:
```c
int test() {
    int a = 10;
    int b = 20;
    return a + b;
}
```

You should see something like:
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
    
    ; Load a from slot 0
    MOV RAX, [R12]
    ; ... add b ...
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

## Common Issues

- **No STACK_BASE**: Check `_generate_data_section()` includes it
- **No R12/R13**: Check function prologue generation
- **Still using RBP-offset**: Old code path, check `_generate_local_var_load/store()`
- **Not 16-byte aligned**: Check slot allocation uses `INC R13` and displacement is `slot_index * 16`

## Success Criteria

✅ All local variables use `[R12 + displacement]` addressing  
✅ Displacements are multiples of 16 (0, 16, 32, 48, ...)  
✅ R13 tracks slot count and is reset in epilogue  
✅ Comments explain the indexed stack system  
✅ Stack base is defined and loaded into R12
