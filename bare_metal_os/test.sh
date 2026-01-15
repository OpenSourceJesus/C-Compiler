#!/bin/bash
# Test script for bare metal OS compilation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Bare Metal OS Compilation Test ==="
echo ""

# Check dependencies
echo "0. Checking dependencies..."
if ! python3 -c "import pycparser" 2>/dev/null; then
    echo "WARNING: pycparser not found. Installing..."
    pip3 install -q pycparser pycparser-fake-libc 2>/dev/null || {
        echo "ERROR: Could not install dependencies."
        echo "Please run: pip3 install pycparser pycparser-fake-libc"
        exit 1
    }
fi

if ! command -v nasm &> /dev/null && ! command -v yasm &> /dev/null; then
    echo "ERROR: Neither nasm nor yasm found."
    echo "Please install one: sudo apt-get install nasm"
    exit 1
fi

if ! command -v ld &> /dev/null; then
    echo "ERROR: ld linker not found."
    echo "Please install binutils: sudo apt-get install binutils"
    exit 1
fi

echo "✓ Dependencies OK"
echo ""

# Compile the bare metal OS
echo "1. Compiling bare metal OS..."
python3 ../compiler.py . -o kernel.asm --verbose

if [ $? -ne 0 ]; then
    echo "ERROR: Compilation failed!"
    exit 1
fi

echo ""
echo "2. Generated assembly saved to kernel.asm"
echo ""

# Verify linker script was found
if [ -f "linker.ld" ]; then
    echo "✓ Linker script found: linker.ld"
else
    echo "✗ Linker script NOT found"
    exit 1
fi

# Verify assembly files were found
if [ -f "startup.S" ]; then
    echo "✓ Assembly startup file found: startup.S"
else
    echo "✗ Assembly startup file NOT found"
    exit 1
fi

# Verify C files were found
if [ -f "kernel.c" ]; then
    echo "✓ Kernel C file found: kernel.c"
else
    echo "✗ Kernel C file NOT found"
    exit 1
fi

# Check for key features in generated assembly
echo ""
echo "3. Verifying generated assembly..."
echo ""

# Check for _start entry point
if grep -q "_start:" kernel.asm; then
    echo "✓ Entry point (_start) found"
else
    echo "✗ Entry point (_start) NOT found"
fi

# Check for main function
if grep -q "FUNC_main" kernel.asm; then
    echo "✓ Main function (FUNC_main) found"
else
    echo "✗ Main function (FUNC_main) NOT found"
fi

# Check for assembly symbols
if grep -q "interrupt_handler_asm" kernel.asm || grep -q "FUNC_interrupt_handler" kernel.asm; then
    echo "✓ Interrupt handler references found"
else
    echo "✗ Interrupt handler references NOT found"
fi

# Check for stack setup
if grep -q "stack_top\|STACK" kernel.asm; then
    echo "✓ Stack setup found"
else
    echo "✗ Stack setup NOT found"
fi

echo ""
echo "4. Checking object file generation..."
if [ -f "kernel.o" ]; then
    echo "✓ Object file generated: kernel.o"
    
    # Check symbols in object file
    if command -v nm &> /dev/null; then
        echo ""
        echo "Symbols in object file:"
        nm kernel.o | head -20
    fi
else
    echo "✗ Object file NOT generated"
fi

echo ""
echo "5. Checking executable generation..."
if [ -f "kernel" ]; then
    echo "✓ Executable generated: kernel"
    
    # Check file type
    if command -v file &> /dev/null; then
        echo ""
        echo "File type:"
        file kernel
    fi
    
    # Check if it's a valid ELF
    if command -v readelf &> /dev/null; then
        echo ""
        echo "ELF header info:"
        readelf -h kernel | head -15
    fi
else
    echo "✗ Executable NOT generated"
fi

echo ""
echo "=== Test Complete ==="
echo ""
echo "Generated files:"
ls -lh kernel.asm kernel.o kernel 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'

echo ""
echo "To run in QEMU (system mode):"
echo "  python3 ../compiler.py . --qemu-system"
echo ""
echo "To run in QEMU (user mode):"
echo "  python3 ../compiler.py . --qemu"
