# Building and Running the Compiler Output

The compiler generates NASM-style assembly code. To run it, you need to assemble and link it.

## Quick Start

```bash
# Build the assembly file
./build.sh output.asm output

# Run the executable
./output
```

## Manual Steps

### 1. Install Required Tools

**On Debian/Ubuntu:**
```bash
sudo apt-get install nasm binutils
```

**On RHEL/CentOS/Fedora:**
```bash
sudo yum install nasm binutils
# or
sudo dnf install nasm binutils
```

### 2. Assemble the Assembly File

```bash
nasm -f elf64 output.asm -o output.o
```

This creates an object file (`output.o`) from the assembly source.

### 3. Link the Object File

```bash
ld output.o -o output
```

This creates an executable named `output`.

### 4. Run the Executable

```bash
./output
```

## Alternative: Using GCC as Linker

If you need C library functions or want more control, you can use GCC:

```bash
nasm -f elf64 output.asm -o output.o
gcc -nostdlib -static output.o -o output
./output
```

## Troubleshooting

### "nasm: command not found"
Install NASM using the package manager for your distribution (see step 1 above).

### "ld: cannot find entry symbol _start"
The assembly file should have a `_start` label. If it doesn't, you may need to specify a different entry point:
```bash
ld -e main output.o -o output  # Use 'main' as entry point instead
```

### "Segmentation fault" or other runtime errors
- The code may require specific system calls or kernel features
- Check if the code is meant to run in a specific environment (e.g., a kernel, bootloader, or VM)
- For kernel code, you may need to create a bootable image instead of a regular executable

### For Kernel/OS Code
If this is kernel code (like minikraft), you may need to:
1. Create a bootable image
2. Use a bootloader (like GRUB)
3. Run it in a VM (QEMU, VirtualBox, etc.)

See your project's documentation for specific boot instructions.
