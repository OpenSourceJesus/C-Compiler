# Custom C Compiler with Function Call Optimizations

A custom C compiler written in Python using pycparser that implements advanced optimizations to reduce function call overhead.

## Features

1. **Indexed-Jump Function Calls**: Functions smaller than 1024 bytes are co-located in memory and invoked via indexed-jump instructions.

2. **Metamorphic Return Sites**: For functions with a single return site, the caller writes the return address bytes directly into the instruction itself, avoiding stack-based return address storage and saving 8 bytes.

3. **Quantized Call-Backs**: Return sites are memory-aligned to 16 bytes, allowing the offset to be stored in a single byte.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python compiler.py input.c -o output.asm
```

## Architecture

- `parser.py`: C code parsing using pycparser
- `analyzer.py`: Function analysis (size, return sites)
- `codegen.py`: Code generation with optimizations
- `compiler.py`: Main compiler entry point