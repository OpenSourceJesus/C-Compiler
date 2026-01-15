# Deep Call Stack Benchmark

This benchmark compares the performance of GCC with `-O3` optimization against this custom compiler on a program with deep function call stacks.

## Test Program

The benchmark uses `benchmark_deep_call.c`, which features:
- A loop with 10 million iterations
- Deep function call chain: `func1` → `func2` → `func3` → `func4` → `func5` → `func6` → `func7` → `func8`
- Each function performs arithmetic operations and calls the next function in the chain
- This creates a deep call stack that tests function call overhead

## Running the Benchmark

Simply execute:

```bash
./benchmark_deep_call.py
```

Or:

```bash
python3 benchmark_deep_call.py
```

The script will:
1. Compile the test program with GCC `-O3`
2. Compile the test program with the custom compiler
3. Run each version 5 times and measure execution time
4. Compare:
   - Average execution time
   - Executable size
   - Speedup ratio
   - Size ratio

## Requirements

- GCC compiler
- Python 3 (for the custom compiler and benchmark script)
- nasm or yasm (for assembling)
- ld (linker)

## Output

The benchmark will display:
- Compilation status and executable sizes
- Individual run times for each iteration
- Average execution times
- Comparison metrics showing which compiler is faster and produces smaller binaries

## Notes

- The benchmark uses `volatile` variables to prevent aggressive optimizations that might eliminate the function calls
- Execution time is measured using Python's `time.perf_counter()` for high precision (nanosecond accuracy)
- The test program returns a computed value to prevent dead code elimination
- All timing values are displayed with 15 decimal places for maximum precision
