# Custom C Compiler with Function Call Optimizations

A custom C compiler written in Python using pycparser that implements advanced optimizations to reduce function call overhead and enable zero-latency kernel flag access.

## Features

1. **Indexed-Jump Function Calls**: Functions smaller than 1024 bytes are co-located in memory and invoked via indexed-jump instructions.

2. **Metamorphic Return Sites**: For functions with a single return site, the caller writes the return address bytes directly into the instruction itself, avoiding stack-based return address storage and saving 8 bytes.

3. **Quantized Call-Backs**: Return sites are memory-aligned to 16 bytes, allowing the offset to be stored in a single byte.

4. **SIMD Bit-Packing**: Global variables with 1-bit to 7-bit types are automatically packed into the last SIMD register (xmm15), which is typically ignored by standard compilers. This eliminates memory reads for frequently accessed kernel flags.

5. **Zero-Latency Kernels**: Key kernel flags are accessed via inline assembly directly from the SIMD register, eliminating memory reads during hardware interrupt callbacks. This prevents pipeline stalls that occur with traditional global variable access.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python compiler.py input.c -o output.asm
```

## Architecture

- `parser.py`: C code parsing using pycparser, extracts functions and global variables
- `analyzer.py`: Function analysis (size, return sites) and global variable analysis for SIMD bit-packing
- `codegen.py`: Code generation with optimizations including SIMD bit-packing and zero-latency access
- `compiler.py`: Main compiler entry point

## SIMD Bit-Packing Details

Global variables with bit-widths of 1-7 bits are automatically detected and packed into the xmm15 SIMD register. This includes:

- Bit-field declarations (e.g., `int flag : 1`)
- Custom bit-width types (e.g., `int3_t`, `uint5_t`)
- Small integer types that fit in 1-7 bits

The compiler generates:
- Initialization code that packs variables into the SIMD register at startup
- Inline assembly for zero-latency read/write operations
- Special handling for interrupt callback functions (detected by naming patterns like `isr_*`, `irq_*`, `*_handler`, `*_callback`)

## Zero-Latency Access

During interrupt callbacks, accessing packed global variables uses direct SIMD register operations instead of memory reads. This eliminates:
- Memory access latency
- Pipeline stalls
- Cache misses

All operations are register-to-register, providing true zero-latency access for critical kernel flags.