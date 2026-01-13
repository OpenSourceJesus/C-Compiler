#!/bin/bash
# Test script for indexed stack pointer system

echo "=== Testing Indexed Stack Pointer System ==="
echo ""

# Check dependencies
echo "0. Checking dependencies..."
python3 -c "import pycparser" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "WARNING: pycparser not found. Installing..."
    pip3 install -q pycparser pycparser-fake-libc 2>/dev/null || {
        echo "ERROR: Could not install dependencies. Please run: pip3 install pycparser pycparser-fake-libc"
        exit 1
    }
fi
echo "✓ Dependencies OK"
echo ""

# Compile the test file
echo "1. Compiling test_indexed_stack.c..."
python3 compiler.py test_indexed_stack.c -o test_indexed_stack.asm -v

if [ $? -ne 0 ]; then
    echo "ERROR: Compilation failed!"
    echo "Please check that:"
    echo "  1. Dependencies are installed: pip3 install pycparser pycparser-fake-libc"
    echo "  2. test_indexed_stack.c exists"
    exit 1
fi

echo ""
echo "2. Generated assembly saved to test_indexed_stack.asm"
echo ""

# Check for key features in the generated assembly
echo "3. Verifying indexed stack pointer features..."
echo ""

# Check for stack base initialization
if grep -q "STACK_BASE" test_indexed_stack.asm; then
    echo "✓ Stack base address (STACK_BASE) found"
else
    echo "✗ Stack base address (STACK_BASE) NOT found"
fi

# Check for R12 (stack base register) usage
if grep -q "R12" test_indexed_stack.asm; then
    echo "✓ Stack base register (R12) usage found"
else
    echo "✗ Stack base register (R12) usage NOT found"
fi

# Check for R13 (stack index register) usage
if grep -q "R13" test_indexed_stack.asm; then
    echo "✓ Stack index register (R13) usage found"
else
    echo "✗ Stack index register (R13) usage NOT found"
fi

# Check for 16-byte slot allocation
if grep -q "slot.*16" test_indexed_stack.asm || grep -q "16.*slot" test_indexed_stack.asm; then
    echo "✓ 16-byte slot allocation found"
else
    echo "✗ 16-byte slot allocation NOT found"
fi

# Check for indexed addressing pattern
if grep -q "R12.*\+.*\]" test_indexed_stack.asm || grep -q "\[R12" test_indexed_stack.asm; then
    echo "✓ Indexed stack addressing pattern found"
else
    echo "✗ Indexed stack addressing pattern NOT found"
fi

# Check for pointer compression comments
if grep -q "pointer compression\|32 bits\|compressed" test_indexed_stack.asm -i; then
    echo "✓ Pointer compression documentation found"
else
    echo "⚠ Pointer compression documentation not found (optional)"
fi

echo ""
echo "4. Key sections to examine in test_indexed_stack.asm:"
echo "   - Function prologue: Should initialize R12 and R13"
echo "   - Local variable allocation: Should use slot indices"
echo "   - Variable access: Should use [R12 + displacement] addressing"
echo "   - Stack base: Should be defined in .data section"
echo ""

# Show relevant sections
echo "5. Sample output from generated assembly:"
echo "---"
grep -A 5 "STACK_BASE\|Indexed stack\|R12\|R13" test_indexed_stack.asm | head -20
echo "---"
echo ""

echo "Test complete! Review test_indexed_stack.asm for full details."
