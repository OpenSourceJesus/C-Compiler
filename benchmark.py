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
import matplotlib
# Try to use interactive backend if display is available, otherwise use Agg
try:
    if os.environ.get('DISPLAY'):
        matplotlib.use('TkAgg')  # Interactive backend if display available
    else:
        matplotlib.use('Agg')  # Non-interactive backend for headless environments
except:
    matplotlib.use('Agg')  # Fallback to non-interactive backend
import matplotlib.pyplot as plt
from parser import find_c_files
from asm_parser import find_asm_files

# Configuration
DEFAULT_ITERATIONS = 5

def find_assembler(use_32bit=False):
    """Find available assembler (nasm or yasm).
    
    Args:
        use_32bit: If True, return elf32 format instead of elf64
    """
    format_type = 'elf32' if use_32bit else 'elf64'
    if shutil.which('nasm'):
        return ('nasm', format_type)
    elif shutil.which('yasm'):
        return ('yasm', format_type)
    return None

def get_file_size(filepath):
    """Get file size in bytes."""
    try:
        return os.path.getsize(filepath)
    except OSError:
        return 0

def run_benchmark(executable_path, name, iterations, verbose=False):
    """Run benchmark and return statistics.
    
    Args:
        executable_path: Path to the executable to benchmark
        name: Name of the compiler/executable being benchmarked
        iterations: Number of iterations to run
        verbose: If True, print individual run times and progress messages
    """
    times = []
    
    if verbose:
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
            if verbose:
                print(f"   Run {i}: ERROR - Failed to execute: {e}")
            continue
        
        # Check for segmentation fault or other signal kills
        # Python's subprocess.run returns negative signal numbers when a process is killed by a signal
        # (e.g., SIGSEGV = 11 returns -11, SIGINT = 2 returns -2)
        # Shells report these as 128 + signal_number (e.g., SIGSEGV = 139 = 128 + 11)
        # 
        # Note: Exit codes 128-255 can be either:
        # 1. Legitimate program return values (from result % 256)
        # 2. Signal kills (128 + signal_number) - but Python reports these as negative
        # 
        # We check for negative return codes (signal kills from Python) and also
        # check for SIGSEGV in shell format (139) for completeness.
        returncode = result.returncode
        
        # Negative return codes indicate the process was killed by a signal
        # Common signals: SIGSEGV=-11, SIGINT=-2, SIGTERM=-15, etc.
        is_signal_kill = (returncode < 0)
        
        # Also check for SIGSEGV in shell format (139 = 128 + 11)
        is_segfault_shell = (returncode == 139)
        
        if is_signal_kill:
            signal_num = -returncode
            signal_names = {
                11: "SIGSEGV (segmentation fault)",
                2: "SIGINT (interrupt)",
                15: "SIGTERM (termination)",
                9: "SIGKILL (kill)",
            }
            signal_name = signal_names.get(signal_num, f"signal {signal_num}")
            if verbose:
                print(f"   Run {i}: ERROR - Process killed by {signal_name} (return code {returncode})")
            continue
        
        if is_segfault_shell:
            if verbose:
                print(f"   Run {i}: SEGFAULT - Process crashed with return code {returncode}")
            continue
        
        # All non-negative exit codes (0-255) except SIGSEGV (139) are treated as valid
        # program return values. The program ran successfully and completed execution.
        
        end = time.perf_counter()
        elapsed = end - start
        
        if elapsed > 0:
            times.append(elapsed)
            if verbose:
                print(f"   Run {i}: {elapsed:18.15f} seconds")
        else:
            if verbose:
                print(f"   Run {i}: ERROR - Invalid time measurement")
    
    if verbose:
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
    print(f"     Average:  {avg:18.15f} seconds")
    print(f"     Minimum:  {min_time:18.15f} seconds")
    print(f"     Maximum:  {max_time:18.15f} seconds")
    print(f"     Range:    {time_range:18.15f} seconds")
    print()
    
    return {
        'avg': avg,
        'min': min_time,
        'max': max_time,
        'range': time_range,
        'times': times
    }

def visualize_results(gcc_stats, custom_stats, gcc_size, custom_size, opt_level):
    """Create matplotlib visualizations of benchmark results.
    
    Args:
        gcc_stats: Dictionary with GCC benchmark statistics (or None)
        custom_stats: Dictionary with custom compiler statistics (or None)
        gcc_size: GCC executable size in bytes
        custom_size: Custom compiler executable size in bytes
        opt_level: GCC optimization level string
    """
    if gcc_stats is None or custom_stats is None:
        print("Warning: Cannot create visualizations - missing benchmark data")
        return
    
    # Create figure with subplots
    fig = plt.figure(figsize=(15, 10))
    
    # 1. Average execution time comparison (bar chart)
    ax1 = plt.subplot(2, 2, 1)
    compilers = ['GCC ' + opt_level, 'Custom Compiler']
    avg_times = [gcc_stats['avg'], custom_stats['avg']]
    colors = ['#2e86ab', '#a23b72']
    bars = ax1.bar(compilers, avg_times, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax1.set_ylabel('Average Execution Time (seconds)', fontsize=11, fontweight='bold')
    ax1.set_title('Average Execution Time Comparison', fontsize=12, fontweight='bold', pad=15)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    
    # Add value labels on bars
    for bar, time_val in zip(bars, avg_times):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{time_val:.6f}s',
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # 2. Individual run times (line plot with markers)
    ax2 = plt.subplot(2, 2, 2)
    gcc_runs = list(range(1, len(gcc_stats['times']) + 1))
    custom_runs = list(range(1, len(custom_stats['times']) + 1))
    ax2.plot(gcc_runs, gcc_stats['times'], marker='o', linestyle='-', 
             label='GCC ' + opt_level, color='#2e86ab', linewidth=2, markersize=6)
    ax2.plot(custom_runs, custom_stats['times'], marker='s', linestyle='-', 
             label='Custom Compiler', color='#a23b72', linewidth=2, markersize=6)
    ax2.set_xlabel('Run Number', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Execution Time (seconds)', fontsize=11, fontweight='bold')
    ax2.set_title('Individual Run Times', fontsize=12, fontweight='bold', pad=15)
    ax2.legend(loc='best', fontsize=10)
    ax2.grid(alpha=0.3, linestyle='--')
    
    # 3. Executable size comparison (bar chart)
    ax3 = plt.subplot(2, 2, 3)
    sizes = [gcc_size, custom_size]
    bars = ax3.bar(compilers, sizes, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax3.set_ylabel('Executable Size (bytes)', fontsize=11, fontweight='bold')
    ax3.set_title('Executable Size Comparison', fontsize=12, fontweight='bold', pad=15)
    ax3.grid(axis='y', alpha=0.3, linestyle='--')
    
    # Add value labels on bars
    for bar, size_val in zip(bars, sizes):
        height = bar.get_height()
        # Format size nicely (KB if > 1024)
        if size_val >= 1024:
            size_str = f'{size_val/1024:.2f} KB\n({size_val:,} bytes)'
        else:
            size_str = f'{size_val:,} bytes'
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                size_str,
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # 4. Performance ratio and statistics
    ax4 = plt.subplot(2, 2, 4)
    ax4.axis('off')
    
    # Calculate ratios
    speedup_ratio = custom_stats['avg'] / gcc_stats['avg']
    size_ratio = custom_size / gcc_size if gcc_size > 0 else 0
    
    # Build statistics text
    stats_text = "Performance Statistics\n" + "=" * 30 + "\n\n"
    stats_text += f"Speedup Ratio: {speedup_ratio:.4f}x\n"
    if speedup_ratio < 1.0:
        percent_faster = ((gcc_stats['avg'] - custom_stats['avg']) / gcc_stats['avg']) * 100
        stats_text += f"Custom is {percent_faster:.2f}% FASTER\n\n"
    else:
        percent_slower = ((custom_stats['avg'] - gcc_stats['avg']) / gcc_stats['avg']) * 100
        stats_text += f"Custom is {percent_slower:.2f}% SLOWER\n\n"
    
    stats_text += f"Size Ratio: {size_ratio:.4f}x\n"
    if size_ratio < 1.0:
        percent_smaller = ((gcc_size - custom_size) / gcc_size) * 100
        stats_text += f"Custom is {percent_smaller:.2f}% SMALLER\n\n"
    else:
        percent_larger = ((custom_size - gcc_size) / gcc_size) * 100
        stats_text += f"Custom is {percent_larger:.2f}% LARGER\n\n"
    
    stats_text += "Time Statistics:\n"
    stats_text += f"  GCC Min: {gcc_stats['min']:.6f}s\n"
    stats_text += f"  GCC Max: {gcc_stats['max']:.6f}s\n"
    stats_text += f"  Custom Min: {custom_stats['min']:.6f}s\n"
    stats_text += f"  Custom Max: {custom_stats['max']:.6f}s\n"
    
    ax4.text(0.1, 0.5, stats_text, fontsize=10, family='monospace',
             verticalalignment='center', bbox=dict(boxstyle='round', 
             facecolor='wheat', alpha=0.5))
    
    # Overall title
    fig.suptitle('Benchmark Results: GCC vs Custom Compiler', 
                 fontsize=14, fontweight='bold', y=0.995)
    
    # Adjust layout
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    
    # Save figure
    script_dir = Path(__file__).parent.absolute()
    output_file = script_dir / 'benchmark_results.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    
    # Display the plot (if running interactively and display is available)
    try:
        if os.environ.get('DISPLAY'):
            plt.show(block=False)  # Non-blocking display
    except Exception as e:
        # If display is not available, just save the file
        pass
    
    plt.close()

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

def compile_and_benchmark(test_path, output_base_name, exclude_patterns=None, use_32bit=False, opt_level='-O0', iterations=DEFAULT_ITERATIONS, enable_metamorphic_return_sites=True, enable_indexed_function_calls=True, include_paths=None):
    """Compile a single file or folder and run benchmarks.
    
    Args:
        test_path: Path to file or directory to compile
        output_base_name: Base name for output files
        exclude_patterns: List of patterns to exclude from compilation (e.g., ['idt_asm.S'])
        use_32bit: If True, compile in 32-bit mode with -m32 flag
        opt_level: GCC optimization level (e.g., '-O2', '-O3', '-Os')
        iterations: Number of benchmark iterations to run
        enable_metamorphic_return_sites: If True, enable metamorphic return sites optimization
        enable_indexed_function_calls: If True, use indexed jump table for small function calls
    """
    test_path = Path(test_path).resolve()
    script_dir = Path(__file__).parent.absolute()
    
    if exclude_patterns is None:
        exclude_patterns = []
    
    if include_paths is None:
        include_paths = []
    
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
            return {'success': False}
    elif test_path.is_dir():
        # Recursively find all .c files in directory and subdirectories
        try:
            c_files = find_c_files(test_path)
            if not c_files:
                print(f"Error: No .c files found in {test_path}")
                return {'success': False}
        except Exception as e:
            print(f"Error finding C files: {e}")
            return {'success': False}
        
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
        return {'success': False}
    
    if linker_scripts:
        pass  # Linker scripts found but not printing
    
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
    # Check if any assembly file defines _start (custom startup)
    has_custom_startup = False
    if asm_files:
        for asm_file in asm_files:
            try:
                with open(asm_file, 'r') as f:
                    content = f.read()
                    # Check for _start definition (global _start or _start:)
                    if '.global _start' in content or '_start:' in content:
                        has_custom_startup = True
                        break
            except Exception:
                pass
    
    # Try compilation, and if it fails with assembly errors, retry with 32-bit mode
    gcc_compiled = False
    
    try:
        # Build GCC command with all C files and assembly files
        gcc_cmd = ['gcc', opt_level, '-DGCC']
        if use_32bit:
            gcc_cmd.append('-m32')
        # Use -nostdlib if custom startup is detected to avoid _start conflict
        if has_custom_startup:
            gcc_cmd.append('-nostdlib')
        # Add include paths
        for include_path in include_paths:
            # Resolve to absolute path for GCC
            abs_include_path = Path(include_path).resolve()
            gcc_cmd.extend(['-I', str(abs_include_path)])
        gcc_cmd.extend(c_files)
        gcc_cmd.extend(asm_files)
        gcc_cmd.extend(['-o', str(gcc_output)])
        
        result = subprocess.run(
            gcc_cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=script_dir
        )
        gcc_compiled = True
    except subprocess.CalledProcessError as e:
        # Check if we should retry with 32-bit mode
        should_retry_32bit = False
        error_text = ""
        
        if e.stderr:
            error_text = e.stderr
            # Extract actual errors (lines containing "Error:")
            error_lines = [line for line in e.stderr.split('\n') if 'Error:' in line]
            # Also check all stderr lines for linker/PIE errors
            all_stderr_lines = [line for line in e.stderr.split('\n') if line.strip()]
            
            # Check if errors suggest 32-bit mode is needed
            # Look for assembly-related errors that might be fixed by 32-bit mode
            has_asm_errors = any(
                'no such instruction' in line.lower() or
                'too many memory references' in line.lower() or
                '64-bit mode' in line or
                'not supported in 64-bit' in line or
                'invalid instruction suffix' in line.lower() or
                'operand type mismatch' in line.lower()
                for line in error_lines
            )
            
            # Also check for PIE/linker errors that might be fixed by 32-bit mode
            has_pie_errors = any(
                'pie' in line.lower() or
                ('relocation' in line.lower() and 'x86_64' in line and 'can not be used' in line.lower()) or
                ('relocation' in line.lower() and 'r_x86_64' in line.lower()) or
                'failed to set dynamic section sizes' in line.lower() or
                'collect2: error: ld returned' in line.lower()
                for line in all_stderr_lines
            )
            
            # Retry with 32-bit mode if:
            # - We have assembly errors AND there are assembly files, OR
            # - We have PIE errors (can occur even without assembly files)
            if not use_32bit:
                if (has_asm_errors and asm_files) or has_pie_errors:
                    should_retry_32bit = True
            
            # Only print errors if we're not going to retry
            if not should_retry_32bit:
                if error_lines:
                    print("Error: GCC compilation failed")
                    print(f"   Compilation errors found:")
                    for error_line in error_lines[:20]:  # Show first 20 errors
                        print(f"   {error_line}")
                    if len(error_lines) > 20:
                        print(f"   ... and {len(error_lines) - 20} more errors")
                else:
                    # If no "Error:" lines, show last part of stderr
                    stderr_lines = e.stderr.split('\n')
                    print("Error: GCC compilation failed")
                    print(f"   Last {min(30, len(stderr_lines))} lines of output:")
                    for line in stderr_lines[-30:]:
                        if line.strip():
                            print(f"   {line}")
        if e.stdout:
            # Sometimes errors go to stdout
            stdout_lines = e.stdout.split('\n')
            error_lines = [line for line in stdout_lines if 'Error:' in line]
            all_stdout_lines = [line for line in stdout_lines if line.strip()]
            if error_lines and not error_text:
                # Check if we should retry with 32-bit
                if not use_32bit:
                    has_asm_errors = any(
                        'no such instruction' in line.lower() or
                        'too many memory references' in line.lower() or
                        'operand type mismatch' in line.lower()
                        for line in error_lines
                    )
                    # Also check for PIE/linker errors in stdout
                    has_pie_errors = any(
                        'pie' in line.lower() or
                        ('relocation' in line.lower() and 'x86_64' in line and 'can not be used' in line.lower()) or
                        ('relocation' in line.lower() and 'r_x86_64' in line.lower()) or
                        'failed to set dynamic section sizes' in line.lower() or
                        'collect2: error: ld returned' in line.lower()
                        for line in all_stdout_lines
                    )
                    # Retry if we have assembly errors with assembly files, or PIE errors
                    if (has_asm_errors and asm_files) or has_pie_errors:
                        should_retry_32bit = True
                
                # Only print errors if we're not going to retry
                if not should_retry_32bit:
                    print("Error: GCC compilation failed")
                    print(f"   Errors from stdout:")
                    for error_line in error_lines[:10]:
                        print(f"   {error_line}")
        
        # Retry with 32-bit mode if needed
        if should_retry_32bit:
            use_32bit = True
            try:
                # Build GCC command again with -m32 flag
                gcc_cmd = ['gcc', opt_level, '-DGCC', '-m32']
                # Use -nostdlib if custom startup is detected to avoid _start conflict
                if has_custom_startup:
                    gcc_cmd.append('-nostdlib')
                # Add include paths
                for include_path in include_paths:
                    # Resolve to absolute path for GCC
                    abs_include_path = Path(include_path).resolve()
                    gcc_cmd.extend(['-I', str(abs_include_path)])
                gcc_cmd.extend(c_files)
                gcc_cmd.extend(asm_files)
                gcc_cmd.extend(['-o', str(gcc_output)])
                
                result = subprocess.run(
                    gcc_cmd,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=script_dir
                )
                gcc_compiled = True
            except subprocess.CalledProcessError as e2:
                print("Error: GCC compilation failed even with 32-bit mode")
                if e2.stderr:
                    # Extract actual errors (lines containing "Error:")
                    error_lines = [line for line in e2.stderr.split('\n') if 'Error:' in line]
                    if error_lines:
                        print(f"   Compilation errors found:")
                        for error_line in error_lines[:20]:  # Show first 20 errors
                            print(f"   {error_line}")
                        if len(error_lines) > 20:
                            print(f"   ... and {len(error_lines) - 20} more errors")
                    else:
                        # If no "Error:" lines, show last part of stderr
                        stderr_lines = e2.stderr.split('\n')
                        print(f"   Last {min(30, len(stderr_lines))} lines of output:")
                        for line in stderr_lines[-30:]:
                            if line.strip():
                                print(f"   {line}")
                if e2.stdout:
                    # Sometimes errors go to stdout
                    stdout_lines = e2.stdout.split('\n')
                    error_lines = [line for line in stdout_lines if 'Error:' in line]
                    if error_lines:
                        print(f"   Errors from stdout:")
                        for error_line in error_lines[:10]:
                            print(f"   {error_line}")
                return {'success': False}
        
        if not gcc_compiled:
            return {'success': False}
    except FileNotFoundError:
        print("Error: gcc not found")
        return {'success': False}
    
    gcc_executable = gcc_output.resolve()
    if not gcc_executable.exists():
        print(f"Error: GCC executable was not created at {gcc_executable}")
        return {'success': False}
    
    # Make sure it's executable
    os.chmod(gcc_executable, 0o755)
    
    gcc_size = get_file_size(gcc_executable)
    
    # Compile with custom compiler
    python_cmd = 'python3'
    
    # Pass the directory or file path to the compiler
    # The compiler already handles directories and recursively finds files
    if test_path.is_dir():
        input_path = str(test_path)
    else:
        input_path = str(test_path.resolve())
    
    custom_asm_file = custom_output_dir / f'{custom_output_name}.asm'
    
    # Build compiler command with 32-bit flag if needed
    compiler_cmd = [python_cmd, 'compiler.py', input_path, '-o', str(custom_asm_file), '--no-assemble']
    if use_32bit:
        compiler_cmd.append('--32-bit')
    if not enable_metamorphic_return_sites:
        compiler_cmd.append('--no-metamorphic-return-sites')
    if not enable_indexed_function_calls:
        compiler_cmd.append('--no-indexed-function-calls')
    # Add include paths
    for include_path in include_paths:
        compiler_cmd.extend(['-I', include_path])
    
    try:
        result = subprocess.run(
            compiler_cmd,
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
        return {'success': False}
    except FileNotFoundError:
        print("Error: Python not found")
        return {'success': False}
    
    # Check if assembly file was created
    asm_file = custom_asm_file
    if not asm_file.exists():
        print(f"Error: Assembly file was not created: {asm_file}")
        return {'success': False}
    
    custom_asm_size = get_file_size(asm_file)
    
    # Assemble and link
    assembler_info = find_assembler(use_32bit)
    if not assembler_info:
        print("Error: Neither nasm nor yasm found")
        return {'success': False}
    
    assembler, format_type = assembler_info
    
    custom_obj_file = custom_output_dir / f'{custom_output_name}.o'
    
    assembler_cmd = [assembler, '-f', format_type, str(asm_file), '-o', str(custom_obj_file)]
    
    try:
        result = subprocess.run(
            assembler_cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=script_dir
        )
    except subprocess.CalledProcessError as e:
        error_text = e.stderr if e.stderr else ""
        all_error_lines = [line for line in error_text.split('\n') if line.strip()]
        
        # Check for address size errors that might be fixed by 32-bit mode
        has_addr_size_errors = any(
            'impossible combination of address sizes' in line.lower() or
            'invalid combination of opcode and operands' in line.lower() or
            '32-bit' in line.lower() and '64-bit' in line.lower() and 'invalid' in line.lower()
            for line in all_error_lines
        )
        
        if has_addr_size_errors and not use_32bit:
            print("Error: Assembly failed (address size mismatch)")
            if e.stderr:
                print(f"   Error output: {e.stderr[:500]}")  # Show first 500 chars
            print()
            print("   Detected address size errors. Retrying with 32-bit mode...")
            # Clean up files
            if asm_file.exists():
                asm_file.unlink()
            if obj_file.exists():
                obj_file.unlink()
            # Recursively retry with 32-bit mode
            return compile_and_benchmark(test_path, output_base_name, exclude_patterns, True, opt_level, iterations)
        
        print("Error: Assembly failed")
        if e.stderr:
            print(f"   Error output: {e.stderr}")
        return {'success': False}
    
    # Check if object file was created
    obj_file = custom_obj_file
    if not obj_file.exists():
        print(f"Error: Object file was not created: {obj_file}")
        return {'success': False}
    
    # Assemble any .S files separately (they use GCC-style assembly, not nasm)
    # Use the same 32-bit mode that was used for GCC compilation
    asm_obj_files = []
    for asm_file in asm_files:
        if asm_file.endswith('.S') or asm_file.endswith('.s'):
            # Create object file name in custom output directory
            asm_obj = custom_output_dir / Path(asm_file).name.replace('.S', '.o').replace('.s', '.o')
            try:
                # Use gcc to assemble .S files (it handles both .S and .s)
                # Use the same 32-bit mode that was determined during GCC compilation
                # Don't define GCC for custom compiler - it needs FUNC_ prefixes
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
    
    # Add 32-bit emulation if needed
    if use_32bit:
        link_cmd.insert(1, '-m')
        link_cmd.insert(2, 'elf_i386')
    
    # Add linker script if found (use the first one if multiple)
    if linker_scripts:
        link_cmd.extend(['-T', linker_scripts[0]])
    
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
        # Check if this is an architecture mismatch error that can be fixed with 32-bit mode
        error_text = e.stderr if e.stderr else ""
        is_arch_mismatch = (
            'i386 architecture' in error_text and 'x86-64' in error_text and
            'incompatible' in error_text.lower()
        ) or (
            'architecture' in error_text.lower() and 'incompatible' in error_text.lower()
        )
        
        # If we're not in 32-bit mode and see an architecture mismatch, retry with 32-bit
        if is_arch_mismatch and not use_32bit:
            print("Error: Linking failed (architecture mismatch)")
            if e.stderr:
                print(f"   Error output: {e.stderr}")
            print()
            print("   Detected architecture mismatch. Retrying with 32-bit mode...")
            # Clean up the object file that was created with wrong architecture
            if obj_file.exists():
                obj_file.unlink()
            # Recursively retry with 32-bit mode
            return compile_and_benchmark(test_path, output_base_name, exclude_patterns, True, opt_level, iterations)
        
        # Check for undefined symbol errors that might indicate we need to retry
        error_text = e.stderr if e.stderr else ""
        has_undefined_symbols = any(
            'undefined reference' in line.lower() and 'FUNC_' in line
            for line in error_text.split('\n')
        )
        
        # If we see undefined FUNC_ symbols and we're using the custom compiler,
        # it means the assembly wasn't generated correctly or the .S file needs GCC define
        # This shouldn't happen if everything is working, but let's handle it
        if has_undefined_symbols and not use_32bit and asm_files:
            print("Error: Linking failed (undefined symbols)")
            if e.stderr:
                print(f"   Error output: {e.stderr}")
            print()
            print("   Detected undefined symbols. This might be a 32/64-bit mismatch issue.")
            print("   However, undefined FUNC_ symbols suggest an issue with symbol generation.")
            # Don't retry automatically - this is likely a bug that needs fixing
        
        print("Error: Linking failed")
        if e.stderr:
            print(f"   Error output: {e.stderr}")
        return {'success': False}
    except FileNotFoundError:
        print("Error: ld linker not found")
        return {'success': False}
    
    custom_executable = custom_output.resolve()
    if not custom_executable.exists():
        print(f"Error: Custom compiler executable was not created at {custom_executable}")
        return {'success': False}
    
    # Make sure it's executable
    os.chmod(custom_executable, 0o755)
    
    custom_size = get_file_size(custom_executable)
    
    # Verify that both executables have the same bitness
    try:
        # Check GCC executable bitness
        gcc_file_result = subprocess.run(
            ['file', str(gcc_executable)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=script_dir
        )
        gcc_is_32bit = '32-bit' in gcc_file_result.stdout
        
        # Check custom executable bitness
        custom_file_result = subprocess.run(
            ['file', str(custom_executable)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=script_dir
        )
        custom_is_32bit = '32-bit' in custom_file_result.stdout
        
        # If bitness doesn't match, retry with the correct mode
        if gcc_is_32bit != custom_is_32bit:
            expected_32bit = gcc_is_32bit  # Use GCC's bitness as the reference
            if use_32bit != expected_32bit:
                print(f"Warning: Bitness mismatch detected!")
                print(f"  GCC executable: {'32-bit' if gcc_is_32bit else '64-bit'}")
                print(f"  Custom executable: {'32-bit' if custom_is_32bit else '64-bit'}")
                print(f"  Retrying with {'32-bit' if expected_32bit else '64-bit'} mode to match GCC...")
                # Clean up mismatched files
                for ext in ['', '.o', '.asm']:
                    for output in [gcc_output, custom_output]:
                        path = Path(f"{output}{ext}")
                        if path.exists():
                            path.unlink()
                # Recursively retry with the correct bitness
                return compile_and_benchmark(test_path, output_base_name, exclude_patterns, expected_32bit, opt_level, iterations, enable_metamorphic_return_sites, include_paths)
    except (subprocess.CalledProcessError, FileNotFoundError):
        # If 'file' command is not available, skip the check
        pass
    
    # Run benchmarks
    gcc_avg = run_benchmark(str(gcc_executable), f"GCC {opt_level}", iterations, verbose=False)
    custom_avg = run_benchmark(str(custom_executable), "Custom Compiler", iterations, verbose=False)
    
    # Results summary
    print(f"GCC {opt_level}:")
    if gcc_avg is not None:
        print(f"  Average time:  {gcc_avg['avg']:18.15f} seconds")
    else:
        print("  Average time: ERROR - Could not measure")
    print(f"  Executable size: {gcc_size} bytes")
    print()
    print(f"Custom Compiler (metamorphic: {'on' if enable_metamorphic_return_sites else 'off'}, indexed calls: {'on' if enable_indexed_function_calls else 'off'}):")
    if custom_avg is not None:
        print(f"  Average time:  {custom_avg['avg']:18.15f} seconds")
    else:
        print("  Average time: ERROR - Could not measure")
    print(f"  Executable size: {custom_size} bytes")
    print(f"  Assembly size:   {custom_asm_size} bytes")
    print()
    
    # Calculate comparisons
    if gcc_avg is not None and custom_avg is not None and gcc_avg['avg'] > 0:
        speedup = custom_avg['avg'] / gcc_avg['avg']
        time_diff = custom_avg['avg'] - gcc_avg['avg']
        
        print(f"Speedup ratio (Custom/GCC): {speedup:.15f}x")
        print(f"Time difference: {time_diff:+.15f} seconds (Custom - GCC)")
        
        if custom_avg['avg'] < gcc_avg['avg']:
            percent_faster = ((gcc_avg['avg'] - custom_avg['avg']) / gcc_avg['avg']) * 100
            print(f"  -> Custom compiler is {percent_faster:.2f}% FASTER")
        else:
            percent_slower = ((custom_avg['avg'] - gcc_avg['avg']) / gcc_avg['avg']) * 100
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
    
    # Create visualizations
    visualize_results(gcc_avg, custom_avg, gcc_size, custom_size, opt_level)
    
    # Check if either benchmark failed (e.g., due to segmentation faults)
    if gcc_avg is None or custom_avg is None:
        print("Error: Benchmark failed - one or more executables crashed (segmentation fault or other error)")
        return {
            'success': False,
            'gcc_avg': gcc_avg,
            'custom_avg': custom_avg,
            'gcc_size': gcc_size,
            'custom_size': custom_size,
            'custom_asm_size': custom_asm_size,
            'metamorphic_enabled': enable_metamorphic_return_sites,
            'indexed_calls_enabled': enable_indexed_function_calls
        }
    
    # Return results for comparison
    return {
        'success': True,
        'gcc_avg': gcc_avg,
        'custom_avg': custom_avg,
        'gcc_size': gcc_size,
        'custom_size': custom_size,
        'custom_asm_size': custom_asm_size,
        'metamorphic_enabled': enable_metamorphic_return_sites,
        'indexed_calls_enabled': enable_indexed_function_calls
    }

def main():
    """Main benchmark function."""
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    
    # Parse command-line arguments
    exclude_patterns = []
    use_32bit = False
    opt_level = '-O0'  # Default optimization level
    iterations = DEFAULT_ITERATIONS
    include_paths = []
    
    args = sys.argv[1:]
    if not args:
        # Default to benchmark_deep_call.c if it exists
        default_test = script_dir / "benchmark_deep_call.c"
        if default_test.exists():
            test_path = default_test
            output_base = "benchmark"
        else:
            print("Usage: benchmark.py <path_to_file_or_folder> [output_base_name] [--exclude PATTERN] [--32bit] [--opt-level LEVEL] [--runs N] [-I DIR]...")
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
            print("  benchmark.py test.c -I include -I lib")
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
        if i < len(args) and not args[i].startswith('-'):
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
            elif args[i] == '-I':
                if i + 1 < len(args):
                    include_paths.append(args[i + 1])
                    i += 2
                else:
                    print(f"Error: -I flag requires a directory path", file=sys.stderr)
                    sys.exit(1)
            else:
                # Unknown flag, skip it
                i += 1
        
        if test_path is None:
            print("Error: No test path specified")
            print("Usage: benchmark.py <path_to_file_or_folder> [output_base_name] [--exclude PATTERN] [--32bit] [--opt-level LEVEL] [--runs N] [-I DIR]...")
            sys.exit(1)
    
    # Print configuration info (but keep it minimal)
    if exclude_patterns:
        print(f"Excluding files matching: {', '.join(exclude_patterns)}")
    if use_32bit:
        print("Compilation mode: 32-bit")
    if include_paths:
        print(f"Include paths: {', '.join(include_paths)}")
    print()
    
    # Run benchmark with metamorphic return sites enabled
    print("=" * 70)
    print("Running benchmark WITH metamorphic return sites")
    print("=" * 70)
    result_with = compile_and_benchmark(test_path, output_base, exclude_patterns, use_32bit, opt_level, iterations, enable_metamorphic_return_sites=True, enable_indexed_function_calls=True, include_paths=include_paths)
    
    if not result_with or not isinstance(result_with, dict) or not result_with.get('success', False):
        print("Error: Benchmark with metamorphic return sites failed")
        sys.exit(1)
    
    print()
    print("=" * 70)
    print("Running benchmark WITHOUT metamorphic return sites")
    print("=" * 70)
    result_without = compile_and_benchmark(test_path, output_base + "_no_metamorphic", exclude_patterns, use_32bit, opt_level, iterations, enable_metamorphic_return_sites=False, enable_indexed_function_calls=True, include_paths=include_paths)
    
    if not result_without or not isinstance(result_without, dict) or not result_without.get('success', False):
        print("Error: Benchmark without metamorphic return sites failed")
        sys.exit(1)
    
    # Compare results
    print()
    print("=" * 70)
    print("Comparison: Metamorphic Return Sites ON vs OFF")
    print("=" * 70)
    
    if result_with.get('custom_avg') and result_without.get('custom_avg'):
        with_avg = result_with['custom_avg']['avg']
        without_avg = result_without['custom_avg']['avg']
        
        if with_avg > 0 and without_avg > 0:
            speedup_ratio = without_avg / with_avg
            time_diff = with_avg - without_avg
            percent_change = ((with_avg - without_avg) / without_avg) * 100
            
            print(f"With metamorphic return sites:    {with_avg:18.15f} seconds")
            print(f"Without metamorphic return sites: {without_avg:18.15f} seconds")
            print(f"Speedup ratio (WITH/WITHOUT):     {speedup_ratio:.15f}x")
            print(f"Time difference:                  {time_diff:+.15f} seconds")
            
            if with_avg < without_avg:
                print(f"  -> Metamorphic return sites make code {abs(percent_change):.2f}% FASTER")
            else:
                print(f"  -> Metamorphic return sites make code {abs(percent_change):.2f}% SLOWER")
        
        # Size comparison
        with_size = result_with.get('custom_size', 0)
        without_size = result_without.get('custom_size', 0)
        if with_size > 0 and without_size > 0:
            size_diff = with_size - without_size
            size_ratio = with_size / without_size
            percent_size_change = ((with_size - without_size) / without_size) * 100
            
            print()
            print(f"With metamorphic return sites:    {with_size} bytes")
            print(f"Without metamorphic return sites: {without_size} bytes")
            print(f"Size difference:                  {size_diff:+d} bytes")
            print(f"Size ratio (WITH/WITHOUT):        {size_ratio:.15f}x")
            
            if with_size < without_size:
                print(f"  -> Metamorphic return sites make code {abs(percent_size_change):.2f}% SMALLER")
            else:
                print(f"  -> Metamorphic return sites make code {abs(percent_size_change):.2f}% LARGER")
    
    # Compare indexed function calls ON vs OFF (speed and size)
    print()
    print("=" * 70)
    print("Running benchmark WITH indexed function calls")
    print("=" * 70)
    result_indexed = compile_and_benchmark(test_path, output_base + "_indexed", exclude_patterns, use_32bit, opt_level, iterations, enable_metamorphic_return_sites=True, enable_indexed_function_calls=True, include_paths=include_paths)
    
    if not result_indexed or not isinstance(result_indexed, dict) or not result_indexed.get('success', False):
        print("Error: Benchmark with indexed function calls failed")
    else:
        print()
        print("=" * 70)
        print("Running benchmark WITHOUT indexed function calls")
        print("=" * 70)
        result_no_indexed = compile_and_benchmark(test_path, output_base + "_no_indexed", exclude_patterns, use_32bit, opt_level, iterations, enable_metamorphic_return_sites=True, enable_indexed_function_calls=False, include_paths=include_paths)
        
        if not result_no_indexed or not isinstance(result_no_indexed, dict) or not result_no_indexed.get('success', False):
            print("Error: Benchmark without indexed function calls failed")
        else:
            print()
            print("=" * 70)
            print("Comparison: Indexed function calls ON vs OFF")
            print("=" * 70)
            
            idx_avg = result_indexed.get('custom_avg')
            noidx_avg = result_no_indexed.get('custom_avg')
            idx_size = result_indexed.get('custom_size', 0)
            noidx_size = result_no_indexed.get('custom_size', 0)
            idx_asm = result_indexed.get('custom_asm_size', 0)
            noidx_asm = result_no_indexed.get('custom_asm_size', 0)
            
            if idx_avg and noidx_avg and idx_avg.get('avg') and noidx_avg.get('avg'):
                with_avg = idx_avg['avg']
                without_avg = noidx_avg['avg']
                if without_avg > 0:
                    speed_ratio = with_avg / without_avg
                    time_diff = with_avg - without_avg
                    pct = ((with_avg - without_avg) / without_avg) * 100
                    print(f"With indexed function calls:    {with_avg:18.15f} seconds")
                    print(f"Without indexed function calls: {without_avg:18.15f} seconds")
                    print(f"Speed ratio (indexed / no-indexed): {speed_ratio:.15f}x")
                    print(f"Time difference:                  {time_diff:+.15f} seconds")
                    if with_avg < without_avg:
                        print(f"  -> Indexed function calls are {abs(pct):.2f}% FASTER")
                    else:
                        print(f"  -> Indexed function calls are {abs(pct):.2f}% SLOWER")
            
            if idx_size > 0 and noidx_size > 0:
                size_diff = idx_size - noidx_size
                size_ratio = idx_size / noidx_size
                pct = ((idx_size - noidx_size) / noidx_size) * 100
                print()
                print(f"Executable size with indexed:    {idx_size} bytes")
                print(f"Executable size without indexed: {noidx_size} bytes")
                print(f"Size difference:                 {size_diff:+d} bytes")
                if idx_size < noidx_size:
                    print(f"  -> Indexed function calls produce {abs(pct):.2f}% SMALLER executable")
                else:
                    print(f"  -> Indexed function calls produce {abs(pct):.2f}% LARGER executable")
            
            if idx_asm > 0 and noidx_asm > 0:
                asm_diff = idx_asm - noidx_asm
                pct = ((idx_asm - noidx_asm) / noidx_asm) * 100
                print()
                print(f"Assembly size with indexed:    {idx_asm} bytes")
                print(f"Assembly size without indexed: {noidx_asm} bytes")
                print(f"Assembly size difference:     {asm_diff:+d} bytes")
                if idx_asm < noidx_asm:
                    print(f"  -> Indexed function calls produce {abs(pct):.2f}% SMALLER assembly")
                else:
                    print(f"  -> Indexed function calls produce {abs(pct):.2f}% LARGER assembly")
    
    print()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        print(f"Error: Unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
