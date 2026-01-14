#!/bin/bash
# Script to run compiler output in QEMU (user mode or system mode)

set -e

EXECUTABLE="${1:-output}"
QEMU_MODE="${2:-user}"  # 'user' or 'system'
KERNEL="${3:-}"         # Path to kernel file (for -kernel)
BIOS="${4:-}"           # Path to BIOS file (for -bios)

if [ ! -f "$EXECUTABLE" ]; then
    echo "Error: Executable '$EXECUTABLE' not found"
    echo "Usage: $0 [executable_name] [mode] [kernel] [bios]"
    echo "  Default: $0 output user"
    echo ""
    echo "Modes:"
    echo "  user   - QEMU user mode (default)"
    echo "  system - QEMU system mode"
    echo ""
    echo "System mode options:"
    echo "  $0 output system [kernel_file]     # Use -kernel"
    echo "  $0 output system '' [bios_file]    # Use -bios"
    exit 1
fi

if [ "$QEMU_MODE" = "system" ]; then
    # System mode QEMU
    if ! command -v qemu-system-x86_64 &> /dev/null; then
        echo "Error: qemu-system-x86_64 not found. Install it with:"
        echo "  sudo apt-get install qemu-system-x86    # Debian/Ubuntu"
        echo "  sudo yum install qemu-system-x86          # RHEL/CentOS"
        exit 1
    fi
    
    echo "Running $EXECUTABLE in QEMU system mode..."
    
    # Build QEMU command
    if [ -n "$KERNEL" ]; then
        echo "  Using -kernel: $KERNEL"
        qemu-system-x86_64 -kernel "$KERNEL"
    elif [ -n "$BIOS" ]; then
        echo "  Using -bios: $BIOS"
        qemu-system-x86_64 -bios "$BIOS" -kernel "$EXECUTABLE"
    else
        echo "  Using -kernel: $EXECUTABLE (default)"
        qemu-system-x86_64 -kernel "$EXECUTABLE"
    fi
else
    # User mode QEMU (default)
    if command -v qemu-x86_64 &> /dev/null; then
        echo "Running $EXECUTABLE in QEMU user mode..."
        qemu-x86_64 "$EXECUTABLE"
    elif command -v qemu-system-x86_64 &> /dev/null; then
        echo "Error: qemu-x86_64 not found, but qemu-system-x86_64 is available."
        echo "For user mode emulation (recommended for ELF binaries), install:"
        echo "  sudo apt-get install qemu-user    # Debian/Ubuntu"
        echo "  sudo yum install qemu-user         # RHEL/CentOS"
        echo ""
        echo "Alternatively, run natively:"
        echo "  ./$EXECUTABLE"
        echo ""
        echo "Or use system mode:"
        echo "  $0 $EXECUTABLE system"
        exit 1
    else
        echo "Error: QEMU not found. Install it with:"
        echo "  sudo apt-get install qemu-user    # Debian/Ubuntu (user mode)"
        echo "  sudo yum install qemu-user         # RHEL/CentOS (user mode)"
        exit 1
    fi
fi
