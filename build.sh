#!/bin/bash
# Build script to assemble and link the compiler output

set -e

ASM_FILE="${1:-output.asm}"
OUTPUT="${2:-output}"
RUN_QEMU="${3:-}"

if [ ! -f "$ASM_FILE" ]; then
    echo "Error: Assembly file '$ASM_FILE' not found"
    exit 1
fi

echo "Assembling $ASM_FILE..."

# Check if nasm is available
if command -v nasm &> /dev/null; then
    ASSEMBLER="nasm"
    FORMAT="elf64"
elif command -v yasm &> /dev/null; then
    ASSEMBLER="yasm"
    FORMAT="elf64"
else
    echo "Error: Neither nasm nor yasm found. Please install one:"
    echo "  sudo apt-get install nasm    # Debian/Ubuntu"
    echo "  sudo yum install nasm        # RHEL/CentOS"
    exit 1
fi

# Assemble the file
$ASSEMBLER -f $FORMAT "$ASM_FILE" -o "${OUTPUT}.o"

if [ $? -ne 0 ]; then
    echo "Error: Assembly failed"
    exit 1
fi

echo "Linking ${OUTPUT}.o..."

# Link the object file
ld "${OUTPUT}.o" -o "$OUTPUT"

if [ $? -ne 0 ]; then
    echo "Error: Linking failed"
    exit 1
fi

echo "Success! Executable created: $OUTPUT"
echo ""

# Check if QEMU should be used
if [ "$RUN_QEMU" = "qemu" ] || [ "$RUN_QEMU" = "--qemu" ] || [ "$RUN_QEMU" = "qemu-system" ] || [ "$RUN_QEMU" = "--qemu-system" ]; then
    QEMU_MODE="system"
    if [ "$RUN_QEMU" = "qemu" ] || [ "$RUN_QEMU" = "--qemu" ]; then
        QEMU_MODE="user"
    fi
    
    if [ "$QEMU_MODE" = "system" ]; then
        # System mode QEMU
        if ! command -v qemu-system-x86_64 &> /dev/null; then
            echo "Error: qemu-system-x86_64 not found. Install it with:"
            echo "  sudo apt-get install qemu-system-x86    # Debian/Ubuntu"
            echo "  sudo yum install qemu-system-x86          # RHEL/CentOS"
            exit 1
        fi
        echo "Running in QEMU system mode with -kernel..."
        qemu-system-x86_64 -kernel "$OUTPUT"
    else
        # User mode QEMU
        if command -v qemu-x86_64 &> /dev/null; then
            echo "Running in QEMU user mode..."
            qemu-x86_64 "$OUTPUT"
        elif command -v qemu-system-x86_64 &> /dev/null; then
            echo "Warning: qemu-x86_64 not found, but qemu-system-x86_64 is available."
            echo "For user mode emulation, install: sudo apt-get install qemu-user"
            echo ""
            echo "To run it natively:"
            echo "  ./$OUTPUT"
            echo ""
            echo "Or use system mode:"
            echo "  ./build.sh $ASM_FILE $OUTPUT qemu-system"
        else
            echo "Error: QEMU not found. Install it with:"
            echo "  sudo apt-get install qemu-user    # For user mode (recommended)"
            echo "  sudo apt-get install qemu-system   # For system mode"
            echo ""
            echo "To run it natively:"
            echo "  ./$OUTPUT"
            exit 1
        fi
    fi
else
    echo "To run it:"
    echo "  ./$OUTPUT"
    echo ""
    echo "To run in QEMU user mode:"
    echo "  ./build.sh $ASM_FILE $OUTPUT qemu"
    echo ""
    echo "To run in QEMU system mode with -kernel:"
    echo "  ./build.sh $ASM_FILE $OUTPUT qemu-system"
fi
