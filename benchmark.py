#!/usr/bin/env python3
"""Benchmark script comparing GCC with this compiler."""

import os
import sys
import subprocess
import time
import shutil
import glob
from pathlib import Path
from statistics import mean, stdev
from parser import find_c_files
from asm_parser import find_asm_files

# Configuration
DEFAULT_ITERATIONS = 5

def find_assembler():
    """Find available assembler (nasm or yasm)."""
    if shutil.which('nasm'):
        return ('nasm', 'elf64')
    elif shutil.which('yasm'):
        return ('yasm', 'elf64')
    return None

def get_file_size(filepath):
    """Get file size in bytes."""
    try:
        return os.path.getsize(filepath)
    except OSError:
        return 0

def run_benchmark(executable_path, name, iterations):
    """Run benchmark and return statistics.
    
    Args:
        executable_path: Path to the executable to benchmark
        name: Name of the compiler/executable being benchmarked
        iterations: Number of iterations to run
    """
    times = []
    
    print(f"   Running {name} ({iterations} iterations)...")
    print()
    
    # Ensure executable path is absolute
    if not os.path.isabs(executable_path):
        executable_path = os.path.abspath(executable_path)
    
    # Check if executable exists
    if not os.path.exists(executable_path):
        print(f"   Error: Executable not found: {executable_path}")
        return None
    
    # Check if executable is actually executable
    if not os.access(executable_path, os.X_OK):
        print(f"   Error: File is not executable: {executable_path}")
        return None
    
    for i in range(1, iterations + 1):
        # Use time.perf_counter() for highest precision
        start = time.perf_counter()
        
        # Run the executable, suppressing output
        try:
            result = subprocess.run(
                [executable_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                cwd=os.path.dirname(executable_path) or os.getcwd()
            )
        except Exception as e:
            print(f"   Run {i}: ERROR - Failed to execute: {e}")
            continue
        
        end = time.perf_counter()
        elapsed = end - start
        
        if elapsed > 0:
            times.append(elapsed)
            print(f"   Run {i}: {elapsed:18.15f} seconds")
        else:
            print(f"   Run {i}: ERROR - Invalid time measurement")
    
    print()
    
    if not times:
        print(f"   Error: Could not measure time for {name}")
        return None
    
    # Calculate statistics
    avg = mean(times)
    min_time = min(times)
    max_time = max(times)
    time_range = max_time - min_time
    
    print(f"   {name} Statistics:")
    print(f"     Average: {avg:18.15f} seconds")
    print(f"     Minimum: {min_time:18.15f} seconds")
    print(f"     Maximum: {max_time:18.15f} seconds")
    print(f"     Range:   {time_range:18.15f} seconds")
    print()
    
    return avg

def find_linker_scripts(directory):
    """Recursively find all linker script files (.ld) in a directory."""
    linker_scripts = []
    path = Path(directory)
    
    if not path.exists() or not path.is_dir():
        return linker_scripts
    
    # Recursively find all .ld files
    for ld_file in path.rglob("*.ld"):
        linker_scripts.append(str(ld_file))
    
    # Sort for deterministic order
    linker_scripts.sort()
    
    return linker_scripts

def compile_and_benchmark(test_path, output_base_name, exclude_patterns=None, use_32bit=False, opt_level='-O3', iterations=DEFAULT_ITERATIONS):
    """Compile a single file or folder and run benchmarks.
    
    Args:
        test_path: Path to file or directory to compile
        output_base_name: Base name for output files
        exclude_patterns: List of patterns to exclude from compilation (e.g., ['idt_asm.S'])
        use_32bit: If True, compile in 32-bit mode with -m32 flag
        opt_level: GCC optimization level (e.g., '-O2', '-O3', '-Os')
        iterations: Number of benchmark iterations to run
    """
    test_path = Path(test_path).resolve()
    script_dir = Path(__file__).parent.absolute()
    
    if exclude_patterns is None:
        exclude_patterns = []
    
    # Create separate output directories
    gcc_output_dir = script_dir / 'gcc_output'
    custom_output_dir = script_dir / 'custom_output'
    
    # Create output directories if they don't exist
    gcc_output_dir.mkdir(exist_ok=True)
    custom_output_dir.mkdir(exist_ok=True)
    
    # Determine test files to compile
    c_files = []
    asm_files = []
    linker_scripts = []
    
    if test_path.is_file():
        if test_path.suffix == '.c':
            c_files = [str(test_path)]
        else:
            print(f"Error: {test_path} is not a .c file")
            return False
    elif test_path.is_dir():
        # Recursively find all .c files in directory and subdirectories
        try:
            c_files = find_c_files(test_path)
            if not c_files:
                print(f"Error: No .c files found in {test_path}")
                return False
        except Exception as e:
            print(f"Error finding C files: {e}")
            return False
        
        # Recursively find all assembly files (.S and .s)
        try:
            all_asm_files = find_asm_files(test_path)
            # Filter out excluded files
            asm_files = []
            for asm_file in all_asm_files:
                excluded = False
                for pattern in exclude_patterns:
                    if pattern in asm_file or Path(asm_file).name == pattern:
                        excluded = True
                        break
                if not excluded:
                    asm_files.append(asm_file)
            
            excluded_count = len(all_asm_files) - len(asm_files)
            if excluded_count > 0:
                print(f"Excluded {excluded_count} assembly file(s) matching exclusion patterns")
        except Exception as e:
            print(f"Warning: Error finding assembly files: {e}")
            asm_files = []
        
        # Recursively find all linker scripts
        linker_scripts = find_linker_scripts(test_path)
    else:
        print(f"Error: {test_path} does not exist")
        return False
    
    print(f"Found {len(c_files)} C file(s) to compile:")
    for f in c_files:
        print(f"  - {f}")
    
    if asm_files:
        print(f"Found {len(asm_files)} assembly file(s):")
        for f in asm_files:
            print(f"  - {f}")
    
    if linker_scripts:
        print(f"Found {len(linker_scripts)} linker script(s):")
        for f in linker_scripts:
            print(f"  - {f}")
    
    print()
    
    # Generate base names for output files
    if len(c_files) == 1 and test_path.is_file():
        gcc_output_name = output_base_name
        custom_output_name = output_base_name
    else:
        # For multiple files or directories, use directory name or base name
        if test_path.is_dir():
            gcc_output_name = test_path.name
            custom_output_name = test_path.name
        else:
            gcc_output_name = output_base_name
            custom_output_name = output_base_name
    
    # Full paths for outputs
    gcc_output = gcc_output_dir / gcc_output_name
    custom_output = custom_output_dir / custom_output_name
    
    # Clean up previous builds
    for ext in ['', '.o', '.asm']:
        for output in [gcc_output, custom_output]:
            path = Path(f"{output}{ext}")
            if path.exists():
                path.unlink()
    
    # Compile with GCC
    print(f"1. Compiling with GCC {opt_level}...")
    if use_32bit:
        print("   Using 32-bit compilation mode (-m32)")
    
    try:
        # Build GCC command with all C files and assembly files
        gcc_cmd = ['gcc', opt_level]
        if use_32bit:
            gcc_cmd.append('-m32')
        gcc_cmd.extend(c_files)
        gcc_cmd.extend(asm_files)
        gcc_cmd.extend(['-o', str(gcc_output)])
        
        if len(gcc_cmd) > 10:  # If command is very long, show summary
            mode_str = " (32-bit)" if use_32bit else ""
            print(f"   Running: gcc {opt_level}{mode_str} [{len(c_files)} C files, {len(asm_files)} ASM files] -o {gcc_output}")
            print(f"   Output directory: {gcc_output_dir}")
        else:
            print(f"   Running: {' '.join(gcc_cmd)}")
        result = subprocess.run(
            gcc_cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=script_dir
        )
    except subprocess.CalledProcessError as e:
        print("Error: GCC compilation failed")
        if e.stderr:
            # Extract actual errors (lines containing "Error:")
            error_lines = [line for line in e.stderr.split('\n') if 'Error:' in line]
            if error_lines:
                print(f"   Compilation errors found:")
                for error_line in error_lines[:20]:  # Show first 20 errors
                    print(f"   {error_line}")
                if len(error_lines) > 20:
                    print(f"   ... and {len(error_lines) - 20} more errors")
                
                # Check if errors are related to 64-bit mode and suggest 32-bit mode
                has_64bit_errors = any('64-bit mode' in line or 'not supported in 64-bit' in line for line in error_lines)
                if has_64bit_errors and not use_32bit:
                    print()
                    print("   Suggestion: Some assembly files appear to be 32-bit code.")
                    print("   Try running with --32bit flag to compile in 32-bit mode.")
            else:
                # If no "Error:" lines, show last part of stderr
                stderr_lines = e.stderr.split('\n')
                print(f"   Last {min(30, len(stderr_lines))} lines of output:")
                for line in stderr_lines[-30:]:
                    if line.strip():
                        print(f"   {line}")
        if e.stdout:
            # Sometimes errors go to stdout
            stdout_lines = e.stdout.split('\n')
            error_lines = [line for line in stdout_lines if 'Error:' in line]
            if error_lines:
                print(f"   Errors from stdout:")
                for error_line in error_lines[:10]:
                    print(f"   {error_line}")
        return False
    except FileNotFoundError:
        print("Error: gcc not found")
        return False
    
    gcc_executable = gcc_output.resolve()
    if not gcc_executable.exists():
        print(f"Error: GCC executable was not created at {gcc_executable}")
        return False
    
    # Make sure it's executable
    os.chmod(gcc_executable, 0o755)
    
    gcc_size = get_file_size(gcc_executable)
    print(f"   GCC executable size: {gcc_size} bytes")
    print()
    
    # Compile with custom compiler
    print("2. Compiling with custom compiler...")
    print(f"   Output directory: {custom_output_dir}")
    python_cmd = '/usr/bin/python3'
    
    # Pass the directory or file path to the compiler
    # The compiler already handles directories and recursively finds files
    if test_path.is_dir():
        input_path = str(test_path)
    else:
        input_path = str(test_path.resolve())
    
    custom_asm_file = custom_output_dir / f'{custom_output_name}.asm'
    
    try:
        result = subprocess.run(
            [python_cmd, 'compiler.py', input_path, '-o', str(custom_asm_file), '--no-assemble'],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=script_dir
        )
    except subprocess.CalledProcessError as e:
        print("Error: Custom compiler failed")
        if e.stderr:
            print(f"   Error output: {e.stderr}")
        return False
    except FileNotFoundError:
        print("Error: Python not found")
        return False
    
    # Check if assembly file was created
    asm_file = custom_asm_file
    if not asm_file.exists():
        print(f"Error: Assembly file was not created: {asm_file}")
        return False
    
    # Assemble and link
    assembler_info = find_assembler()
    if not assembler_info:
        print("Error: Neither nasm nor yasm found")
        return False
    
    assembler, format_type = assembler_info
    
    custom_obj_file = custom_output_dir / f'{custom_output_name}.o'
    
    try:
        result = subprocess.run(
            [assembler, '-f', format_type, str(asm_file), '-o', str(custom_obj_file)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=script_dir
        )
    except subprocess.CalledProcessError as e:
        print("Error: Assembly failed")
        if e.stderr:
            print(f"   Error output: {e.stderr}")
        return False
    
    # Check if object file was created
    obj_file = custom_obj_file
    if not obj_file.exists():
        print(f"Error: Object file was not created: {obj_file}")
        return False
    
    # Assemble any .S files separately (they use GCC-style assembly, not nasm)
    asm_obj_files = []
    for asm_file in asm_files:
        if asm_file.endswith('.S') or asm_file.endswith('.s'):
            # Create object file name in custom output directory
            asm_obj = custom_output_dir / Path(asm_file).name.replace('.S', '.o').replace('.s', '.o')
            try:
                # Use gcc to assemble .S files (it handles both .S and .s)
                gcc_asm_cmd = ['gcc', '-c', asm_file, '-o', str(asm_obj)]
                if use_32bit:
                    gcc_asm_cmd.insert(1, '-m32')
                result = subprocess.run(
                    gcc_asm_cmd,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=script_dir
                )
                asm_obj_files.append(str(asm_obj))
            except subprocess.CalledProcessError as e:
                print(f"Warning: Failed to assemble {asm_file}: {e.stderr}")
            except FileNotFoundError:
                print(f"Warning: gcc not found, skipping assembly file {asm_file}")
    
    # Build linker command with all object files
    link_cmd = ['ld', str(obj_file)] + asm_obj_files + ['-o', str(custom_output)]
    
    # Add linker script if found (use the first one if multiple)
    if linker_scripts:
        link_cmd.extend(['-T', linker_scripts[0]])
        print(f"   Using linker script: {linker_scripts[0]}")
    
    try:
        result = subprocess.run(
            link_cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=script_dir
        )
    except subprocess.CalledProcessError as e:
        print("Error: Linking failed")
        if e.stderr:
            print(f"   Error output: {e.stderr}")
        return False
    except FileNotFoundError:
        print("Error: ld linker not found")
        return False
    
    custom_executable = custom_output.resolve()
    if not custom_executable.exists():
        print(f"Error: Custom compiler executable was not created at {custom_executable}")
        return False
    
    # Make sure it's executable
    os.chmod(custom_executable, 0o755)
    
    custom_size = get_file_size(custom_executable)
    print(f"   Custom compiler executable size: {custom_size} bytes")
    print()
    
    # Run benchmarks
    print(f"3. Running benchmarks ({iterations} iterations each)...")
    print()
    
    gcc_avg = run_benchmark(str(gcc_executable), f"GCC {opt_level}", iterations)
    print()
    custom_avg = run_benchmark(str(custom_executable), "Custom Compiler", iterations)
    print()
    
    # Results summary
    print("=" * 50)
    print("Results Summary")
    print("=" * 50)
    print(f"GCC {opt_level}:")
    if gcc_avg is not None:
        print(f"  Average time: {gcc_avg:18.15f} seconds")
    else:
        print("  Average time: ERROR - Could not measure")
    print(f"  Executable size: {gcc_size} bytes")
    print()
    print("Custom Compiler:")
    if custom_avg is not None:
        print(f"  Average time: {custom_avg:18.15f} seconds")
    else:
        print("  Average time: ERROR - Could not measure")
    print(f"  Executable size: {custom_size} bytes")
    print()
    
    # Calculate comparisons
    if gcc_avg is not None and custom_avg is not None and gcc_avg > 0:
        speedup = custom_avg / gcc_avg
        time_diff = custom_avg - gcc_avg
        
        print(f"Speedup ratio (Custom/GCC): {speedup:.15f}x")
        print(f"Time difference: {time_diff:+.15f} seconds (Custom - GCC)")
        
        if custom_avg < gcc_avg:
            percent_faster = ((gcc_avg - custom_avg) / gcc_avg) * 100
            print(f"  -> Custom compiler is {percent_faster:.2f}% FASTER")
        else:
            percent_slower = ((custom_avg - gcc_avg) / gcc_avg) * 100
            print(f"  -> Custom compiler is {percent_slower:.2f}% SLOWER")
        
        print()
        
        if gcc_size > 0:
            size_ratio = custom_size / gcc_size
            size_diff = custom_size - gcc_size
            print(f"Size ratio (Custom/GCC): {size_ratio:.15f}x")
            print(f"Size difference: {size_diff:+d} bytes (Custom - GCC)")
            
            if custom_size < gcc_size:
                percent_smaller = ((gcc_size - custom_size) / gcc_size) * 100
                print(f"  -> Custom compiler produces {percent_smaller:.2f}% SMALLER binary")
            else:
                percent_larger = ((custom_size - gcc_size) / gcc_size) * 100
                print(f"  -> Custom compiler produces {percent_larger:.2f}% LARGER binary")
    
    print()
    print("=" * 50)
    return True

def main():
    """Main benchmark function."""
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    
    # Parse command-line arguments
    exclude_patterns = []
    use_32bit = False
    opt_level = '-O3'  # Default optimization level
    iterations = DEFAULT_ITERATIONS
    
    args = sys.argv[1:]
    if not args:
        # Default to benchmark_deep_call.c if it exists
        default_test = script_dir / "benchmark_deep_call.c"
        if default_test.exists():
            test_path = default_test
            output_base = "benchmark"
        else:
            print("Usage: benchmark.py <path_to_file_or_folder> [output_base_name] [--exclude PATTERN] [--32bit] [--opt-level LEVEL] [--runs N]")
            print()
            print("Examples:")
            print("  benchmark.py test.c")
            print("  benchmark.py test_folder")
            print("  benchmark.py test.c my_test")
            print("  benchmark.py test_folder --exclude idt_asm.S")
            print("  benchmark.py test_folder --32bit")
            print("  benchmark.py test.c --opt-level O2")
            print("  benchmark.py test.c --opt-level O3")
            print("  benchmark.py test.c --opt-level Os")
            print("  benchmark.py test.c --runs 10")
            sys.exit(1)
        args = []
    else:
        # Parse arguments
        test_path = None
        output_base = "benchmark"
        i = 0
        
        # First argument should be the test path
        if args[0] and not args[0].startswith('--'):
            test_path = Path(args[0]).resolve()
            i = 1
        
        # Second argument might be output base name (if not a flag)
        if i < len(args) and not args[i].startswith('--'):
            output_base = args[i]
            i += 1
        
        # Parse flags
        while i < len(args):
            if args[i] == '--exclude' and i + 1 < len(args):
                exclude_patterns.append(args[i + 1])
                i += 2
            elif args[i] == '--32bit':
                use_32bit = True
                i += 1
            elif args[i] == '--opt-level' and i + 1 < len(args):
                opt_level_arg = args[i + 1]
                # Ensure it starts with -O
                if opt_level_arg.startswith('-O'):
                    opt_level = opt_level_arg
                elif opt_level_arg.startswith('O'):
                    opt_level = f'-{opt_level_arg}'
                else:
                    opt_level = f'-O{opt_level_arg}'
                i += 2
            elif args[i] == '--runs' and i + 1 < len(args):
                try:
                    iterations = int(args[i + 1])
                    if iterations < 1:
                        print("Error: Number of runs must be at least 1")
                        sys.exit(1)
                except ValueError:
                    print(f"Error: Invalid number of runs: {args[i + 1]}")
                    sys.exit(1)
                i += 2
            else:
                i += 1
        
        if test_path is None:
            print("Error: No test path specified")
            print("Usage: benchmark.py <path_to_file_or_folder> [output_base_name] [--exclude PATTERN] [--32bit] [--opt-level LEVEL] [--runs N]")
            sys.exit(1)
    
    print("=" * 50)
    print(f"Benchmark: GCC {opt_level} vs Custom Compiler")
    print("=" * 50)
    print()
    print(f"Test path: {test_path}")
    if exclude_patterns:
        print(f"Excluding files matching: {', '.join(exclude_patterns)}")
    if use_32bit:
        print("Compilation mode: 32-bit")
    print(f"GCC optimization level: {opt_level}")
    print(f"Number of benchmark runs: {iterations}")
    print()
    
    success = compile_and_benchmark(test_path, output_base, exclude_patterns, use_32bit, opt_level, iterations)
    
    if not success:
        sys.exit(1)

if __name__ == '__main__':
    main()
