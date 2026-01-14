#!/bin/bash
# Build script to assemble and link the compiler output

set -e

ASM_FILE="${1:-output.asm}"
OUTPUT="${2:-output}"

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
echo "To run it:"
echo "  ./$OUTPUT"
