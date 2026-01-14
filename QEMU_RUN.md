# Running Compiler Output in QEMU

The compiler now supports running compiled executables in QEMU user mode emulation.

## Quick Start

### Option 1: Use the compiler's `--qemu` flag
```bash
python3 compiler.py test_simd_2.c -o test_simd_2 --qemu
```

This will:
1. Compile the C file to assembly
2. Assemble and link it
3. Automatically run it in QEMU user mode

### Option 2: Use the build script with QEMU
```bash
./build.sh output.asm output qemu
```

### Option 3: Use the standalone QEMU runner
```bash
# First compile and build normally
python3 compiler.py test_simd_2.c -o test_simd_2
# Then run in QEMU
./run_qemu.sh test_simd_2
```

## Installation

### Install QEMU User Mode (Recommended)

**On Debian/Ubuntu:**
```bash
sudo apt-get install qemu-user
```

**On RHEL/CentOS/Fedora:**
```bash
sudo yum install qemu-user
# or
sudo dnf install qemu-user
```

### Verify Installation
```bash
qemu-x86_64 --version
```

## What Changed

1. **Fixed `_start` function**: Now properly calls `main()` and exits with the return code
2. **Added exit system call**: Programs now properly terminate using `sys_exit` (syscall 60)
3. **QEMU integration**: Added `--qemu` flag to compiler and helper scripts

## How It Works

The compiler generates ELF64 executables that can run in:
- **Native mode**: Directly on your Linux system (`./output`)
- **QEMU user mode**: Emulated execution (`qemu-x86_64 output`)

QEMU user mode is useful for:
- Testing on different architectures
- Debugging and isolation
- Cross-platform development

## Troubleshooting

### "qemu-x86_64: command not found"
Install QEMU user mode (see Installation section above).

### "qemu-system-x86_64 found but not qemu-x86_64"
You have QEMU system mode but need user mode. Install `qemu-user` package.

### Program crashes or hangs
- Check that your program has a `main()` function
- Verify the program exits properly (the compiler now adds exit system calls automatically)
- Try running natively first: `./output`

### System call errors
QEMU user mode translates system calls to the host system. Some advanced system calls may not be fully supported.
