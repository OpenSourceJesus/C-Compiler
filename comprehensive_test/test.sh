#!/bin/bash
# Test script for comprehensive multi-file test suite

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPILER_DIR="$(dirname "$SCRIPT_DIR")"
TEST_DIR="$SCRIPT_DIR"

echo "=== Comprehensive Multi-File Test Suite ==="
echo ""

# Change to compiler directory
cd "$COMPILER_DIR"

# Compile the test suite
echo "Compiling comprehensive test suite..."
python3 compiler.py "$TEST_DIR" -o "$TEST_DIR/comprehensive_test.asm" -v

echo ""
echo "=== Compilation successful! ==="
echo ""
echo "Generated files:"
echo "  - $TEST_DIR/comprehensive_test.asm"
echo "  - $TEST_DIR/comprehensive_test (executable)"
echo ""
echo "To view the generated assembly:"
echo "  cat $TEST_DIR/comprehensive_test.asm"
echo ""
echo "To run the executable:"
echo "  $TEST_DIR/comprehensive_test"
echo ""

# Check for key features in generated assembly
echo "=== Verifying key features in generated assembly ==="
echo ""

if grep -q "JUMP_TABLE" "$TEST_DIR/comprehensive_test.asm"; then
    echo "✓ Indexed-jump table found"
else
    echo "✗ Indexed-jump table not found"
fi

if grep -q "_init_simd_packing" "$TEST_DIR/comprehensive_test.asm"; then
    echo "✓ SIMD packing initialization found"
else
    echo "✗ SIMD packing initialization not found"
fi

if grep -q "STACK_BASE" "$TEST_DIR/comprehensive_test.asm"; then
    echo "✓ Stack base found"
else
    echo "✗ Stack base not found"
fi

if grep -q "\[R12" "$TEST_DIR/comprehensive_test.asm"; then
    echo "✓ Indexed stack addressing found"
else
    echo "✗ Indexed stack addressing not found"
fi

if grep -q "xmm15" "$TEST_DIR/comprehensive_test.asm"; then
    echo "✓ SIMD register (xmm15) usage found"
else
    echo "✗ SIMD register usage not found"
fi

if grep -q "FUNC_isr_timer_handler\|FUNC_irq_keyboard_handler" "$TEST_DIR/comprehensive_test.asm"; then
    echo "✓ Interrupt callback functions found"
else
    echo "✗ Interrupt callback functions not found"
fi

echo ""
echo "=== Test complete ==="
