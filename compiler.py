#!/usr/bin/env python3
"""Main compiler entry point."""

import argparse
import sys
import os
import subprocess
import shutil
from pathlib import Path
from parser import CParser, MultiFileParser, find_c_files
from analyzer import analyze_all_functions, analyze_global_variables
from codegen import CodeGenerator
from asm_parser import parse_asm_files, find_asm_files
from symbol_collector import collect_symbols


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
	else:
		return None


def find_linker_script(input_path):
	"""Find linker script (linker.ld) in common locations."""
	# Convert to Path object if it's a string
	if isinstance(input_path, str):
		input_path = Path(input_path)
	
	# Resolve to absolute path
	try:
		input_path = input_path.resolve()
	except:
		pass
	
	# Check in the input directory
	if input_path.is_dir():
		linker_script = input_path / 'linker.ld'
		if linker_script.exists():
			return str(linker_script)
		
		# Check in common subdirectories
		for subdir in ['src', 'kernel', 'src/kernel', 'build']:
			linker_script = input_path / subdir / 'linker.ld'
			if linker_script.exists():
				return str(linker_script)
		
		# Check parent directories up to 3 levels
		current = input_path
		for _ in range(3):
			current = current.parent
			linker_script = current / 'linker.ld'
			if linker_script.exists():
				return str(linker_script)
			# Also check subdirectories
			for subdir in ['src', 'kernel', 'src/kernel', 'build']:
				linker_script = current / subdir / 'linker.ld'
				if linker_script.exists():
					return str(linker_script)
	
	# Check parent directory if input is a file
	if input_path.is_file():
		parent = input_path.parent
		linker_script = parent / 'linker.ld'
		if linker_script.exists():
			return str(linker_script)
		
		# Check in common subdirectories of parent
		for subdir in ['src', 'kernel', 'src/kernel', 'build']:
			linker_script = parent / subdir / 'linker.ld'
			if linker_script.exists():
				return str(linker_script)
		
		# Check parent directories up to 3 levels
		current = parent
		for _ in range(3):
			current = current.parent
			linker_script = current / 'linker.ld'
			if linker_script.exists():
				return str(linker_script)
			# Also check subdirectories
			for subdir in ['src', 'kernel', 'src/kernel', 'build']:
				linker_script = current / subdir / 'linker.ld'
				if linker_script.exists():
					return str(linker_script)
	
	# Check for minikraft directory structure in common locations
	minikraft_paths = [
		Path('/home/gileadcosman/pythonlinux/minikraft/src/kernel/linker.ld'),
		Path.home() / 'minikraft' / 'src' / 'kernel' / 'linker.ld',
		Path.home() / 'minikraft' / 'linker.ld',
		Path('/home/gileadcosman/minikraft/src/kernel/linker.ld'),
		Path('/home/gileadcosman/minikraft/linker.ld'),
	]
	
	for path in minikraft_paths:
		if path.exists():
			return str(path)
	
	# Check current working directory
	cwd = Path.cwd()
	linker_script = cwd / 'linker.ld'
	if linker_script.exists():
		return str(linker_script)
	
	# Check in common subdirectories of current directory
	for subdir in ['src', 'kernel', 'src/kernel', 'build']:
		linker_script = cwd / subdir / 'linker.ld'
		if linker_script.exists():
			return str(linker_script)
	
	return None


def assemble_and_link(asm_file, output_executable=None, verbose=False, linker_script=None, use_32bit=False):
	"""Assemble and link the generated assembly file.
	
	Args:
		asm_file: Path to assembly file
		output_executable: Output executable path
		verbose: Enable verbose output
		linker_script: Path to linker script
		use_32bit: If True, use 32-bit mode (elf32, -m elf_i386)
	"""
	# Find assembler
	assembler_info = find_assembler(use_32bit)
	if not assembler_info:
		print("Error: Neither nasm nor yasm found. Please install one:", file=sys.stderr)
		print("  sudo apt-get install nasm    # Debian/Ubuntu", file=sys.stderr)
		print("  sudo yum install nasm        # RHEL/CentOS", file=sys.stderr)
		return False
	
	assembler, format_type = assembler_info
	
	# Determine output object file name
	obj_file = asm_file.replace('.asm', '.o')
	
	# Determine executable name
	if output_executable is None:
		output_executable = asm_file.replace('.asm', '')
	
	# Assemble
	if verbose:
		print(f"Assembling {asm_file}...", file=sys.stderr)
	
	try:
		result = subprocess.run(
			[assembler, '-f', format_type, asm_file, '-o', obj_file],
			check=True,
			capture_output=True,
			text=True
		)
	except subprocess.CalledProcessError as e:
		print(f"Error: Assembly failed", file=sys.stderr)
		if e.stderr:
			print(e.stderr, file=sys.stderr)
		return False
	
	# Link
	if verbose:
		print(f"Linking {obj_file}...", file=sys.stderr)
		if linker_script:
			print(f"Using linker script: {linker_script}", file=sys.stderr)
	
	try:
		# Build linker command
		link_cmd = ['ld', obj_file, '-o', output_executable]
		
		# Add 32-bit emulation if needed
		if use_32bit:
			link_cmd.insert(1, '-m')
			link_cmd.insert(2, 'elf_i386')
		
		# Add linker script if provided
		if linker_script:
			link_cmd.extend(['-T', linker_script])
		
		result = subprocess.run(
			link_cmd,
			check=True,
			capture_output=True,
			text=True
		)
	except subprocess.CalledProcessError as e:
		print(f"Error: Linking failed", file=sys.stderr)
		if e.stderr:
			print(e.stderr, file=sys.stderr)
		return False
	except FileNotFoundError:
		print("Error: 'ld' linker not found. Please ensure binutils is installed.", file=sys.stderr)
		return False
	
	if verbose:
		print(f"Success! Executable created: {output_executable}", file=sys.stderr)
	
	return True


def run_qemu(executable, verbose=False, qemu_mode='user', kernel=None, bios=None):
	"""Run the executable in QEMU.
	
	Args:
		executable: Path to the executable file
		verbose: Enable verbose output
		qemu_mode: 'user' for user mode, 'system' for system mode
		kernel: Path to kernel file (for system mode with -kernel)
		bios: Path to BIOS file (for system mode with -bios)
	"""
	if qemu_mode == 'system':
		# System mode QEMU
		if verbose:
			print(f"Running {executable} in QEMU system mode...", file=sys.stderr)
		
		if not shutil.which('qemu-system-x86_64'):
			print("Error: qemu-system-x86_64 not found. Install it with:", file=sys.stderr)
			print("  sudo apt-get install qemu-system-x86    # Debian/Ubuntu", file=sys.stderr)
			print("  sudo yum install qemu-system-x86          # RHEL/CentOS", file=sys.stderr)
			return False
		
		# Build QEMU command
		cmd = ['qemu-system-x86_64']
		
		# Add BIOS if specified
		if bios:
			cmd.extend(['-bios', bios])
		
		# Add kernel - use specified kernel, or executable as default
		if kernel:
			cmd.extend(['-kernel', kernel])
		else:
			# Default: use -kernel with the executable
			cmd.extend(['-kernel', executable])
		
		try:
			subprocess.run(cmd, check=False)
			return True
		except subprocess.CalledProcessError:
			return False
		except FileNotFoundError:
			return False
	else:
		# User mode QEMU (default)
		if verbose:
			print(f"Running {executable} in QEMU user mode...", file=sys.stderr)
		
		# Check if QEMU user mode is available
		if shutil.which('qemu-x86_64'):
			try:
				subprocess.run(['qemu-x86_64', executable], check=False)
				return True
			except subprocess.CalledProcessError:
				return False
			except FileNotFoundError:
				pass
		
		# QEMU not found or wrong version
		if shutil.which('qemu-system-x86_64'):
			print("Error: qemu-x86_64 not found, but qemu-system-x86_64 is available.", file=sys.stderr)
			print("For user mode emulation (recommended for ELF binaries), install:", file=sys.stderr)
			print("  sudo apt-get install qemu-user    # Debian/Ubuntu", file=sys.stderr)
			print("  sudo yum install qemu-user         # RHEL/CentOS", file=sys.stderr)
		else:
			print("Error: QEMU not found. Install it with:", file=sys.stderr)
			print("  sudo apt-get install qemu-user    # Debian/Ubuntu (user mode)", file=sys.stderr)
			print("  sudo yum install qemu-user         # RHEL/CentOS (user mode)", file=sys.stderr)
		
		return False


def main():
	"""Main compiler entry point."""
	parser = argparse.ArgumentParser(description='Custom C Compiler with Function Call Optimizations')
	parser.add_argument('input_path', help='Input C source file or directory containing C files')
	parser.add_argument('-o', '--output', help='Output assembly file (or executable if --assemble is used)', default=None)
	parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
	parser.add_argument('--no-assemble', action='store_true', help='Skip assembly and linking, only generate assembly file')
	parser.add_argument('--qemu', action='store_true', help='Run the compiled executable in QEMU user mode after building')
	parser.add_argument('--qemu-system', action='store_true', help='Run in QEMU system mode instead of user mode')
	parser.add_argument('--qemu-kernel', help='Path to kernel file for QEMU system mode (-kernel option)')
	parser.add_argument('--qemu-bios', help='Path to BIOS file for QEMU system mode (-bios option)')
	parser.add_argument('--32-bit', dest='use_32bit', action='store_true', help='Generate 32-bit code (elf32 format)')
	
	args = parser.parse_args()
	
	input_path = Path(args.input_path)
	
	# Determine if input is a file or directory
	if input_path.is_file():
		# Single file mode
		c_files = [str(input_path)]
		c_parser = CParser()
		try:
			ast = c_parser.parse_file(args.input_path)
			# for node in ast:
			#     print(f"node: {node}")
			if args.verbose:
				print(f"Parsed {args.input_path} successfully", file=sys.stderr)
		except Exception as e:
			print(f"Error parsing {args.input_path}: {e}", file=sys.stderr)
			sys.exit(1)
	elif input_path.is_dir():
		# Directory mode - find all .c files recursively
		try:
			c_files = find_c_files(args.input_path)
			if not c_files:
				print(f"Error: No .c files found in directory {args.input_path}", file=sys.stderr)
				sys.exit(1)
			
			if args.verbose:
				print(f"Found {len(c_files)} C file(s) in {args.input_path}:", file=sys.stderr)
				for c_file in c_files:
					print(f"  {c_file}", file=sys.stderr)
			
			# Parse all files
			c_parser = MultiFileParser()
			try:
				c_parser.parse_files(c_files)
				if args.verbose:
					print(f"Parsed {len(c_files)} file(s) successfully", file=sys.stderr)
			except Exception as e:
				print(f"Error parsing files: {e}", file=sys.stderr)
				sys.exit(1)
		except Exception as e:
			print(f"Error: {e}", file=sys.stderr)
			sys.exit(1)
	else:
		print(f"Error: {args.input_path} is not a valid file or directory", file=sys.stderr)
		sys.exit(1)
	
	# Analyze functions
	try:
		function_data = analyze_all_functions(c_parser)
		if args.verbose:
			print(f"Analyzed {len(function_data)} functions", file=sys.stderr)
			for name, info in function_data.items():
				print(f"  {name}: size={info['size']} bytes, "
					  f"returns={info['return_sites']}, "
					  f"small={info['is_small']}, "
					  f"single_return={info['has_single_return']}", file=sys.stderr)
	except Exception as e:
		print(f"Error analyzing functions: {e}", file=sys.stderr)
		sys.exit(1)
	
	# Analyze global variables for SIMD bit-packing
	try:
		global_var_data = analyze_global_variables(c_parser)
		if args.verbose:
			packed_count = len(global_var_data['packed_vars'])
			if packed_count > 0:
				print(f"SIMD Bit-Packing: {packed_count} global variables packed into {global_var_data['total_bits_used']} bits", file=sys.stderr)
				for var_info in global_var_data['packed_vars']:
					print(f"  {var_info['name']}: {var_info['bits']} bits at position {var_info['start_bit']}", file=sys.stderr)
	except Exception as e:
		print(f"Error analyzing global variables: {e}", file=sys.stderr)
		global_var_data = {'packed_vars': [], 'bit_positions': {}, 'total_bits_used': 0}
	
	# Parse assembly files if they exist
	asm_parser = None
	if input_path.is_dir():
		# Look for assembly files in the same directory
		asm_files = find_asm_files(input_path)
		if asm_files:
			if args.verbose:
				print(f"Found {len(asm_files)} assembly file(s):", file=sys.stderr)
				for asm_file in asm_files:
					print(f"  {asm_file}", file=sys.stderr)
			try:
				asm_parser = parse_asm_files(asm_files)
				if args.verbose:
					symbols = asm_parser.get_all_symbols()
					if symbols:
						print(f"Extracted {len(symbols)} symbol(s) from assembly files:", file=sys.stderr)
						for symbol in sorted(symbols):
							symbol_info = asm_parser.global_symbols.get(symbol, {})
							symbol_type = symbol_info.get('type', 'unknown')
							print(f"  {symbol} ({symbol_type})", file=sys.stderr)
			except Exception as e:
				print(f"Warning: Failed to parse assembly files: {e}", file=sys.stderr)
				asm_parser = None
	elif input_path.is_file():
		# Look for assembly files in the same directory as the C file
		asm_dir = input_path.parent
		asm_files = find_asm_files(asm_dir)
		if asm_files:
			if args.verbose:
				print(f"Found {len(asm_files)} assembly file(s) in directory:", file=sys.stderr)
				for asm_file in asm_files:
					print(f"  {asm_file}", file=sys.stderr)
			try:
				asm_parser = parse_asm_files(asm_files)
				if args.verbose:
					symbols = asm_parser.get_all_symbols()
					if symbols:
						print(f"Extracted {len(symbols)} symbol(s) from assembly files", file=sys.stderr)
			except Exception as e:
				print(f"Warning: Failed to parse assembly files: {e}", file=sys.stderr)
				asm_parser = None
	
	# Generate code
	try:
		codegen = CodeGenerator(function_data, global_var_data, asm_parser, args.use_32bit)
		output_code = codegen.generate(c_parser)
		
		# Write output
		if args.output:
			output_file = args.output
		elif input_path.is_file():
			output_file = str(input_path).replace('.c', '.asm')
		else:
			# For directories, use directory name with .asm extension
			output_file = os.path.join(args.input_path, Path(args.input_path).name + '.asm')
		
		with open(output_file, 'w') as f:
			f.write(output_code)
		
		if args.verbose:
			print(f"Generated code written to {output_file}", file=sys.stderr)
		
		# Assemble and link if not disabled
		if not args.no_assemble:
			# Determine executable output name
			if args.output:
				# If user specified output, use it for both asm and executable
				executable_name = args.output.replace('.asm', '')
			else:
				# Default executable name based on input
				if input_path.is_file():
					executable_name = str(input_path).replace('.c', '')
				else:
					executable_name = os.path.join(args.input_path, Path(args.input_path).name)
			
			# Find linker script
			linker_script = find_linker_script(input_path)
			if linker_script and args.verbose:
				print(f"Found linker script: {linker_script}", file=sys.stderr)
			
			success = assemble_and_link(output_file, executable_name, args.verbose, linker_script, args.use_32bit)
			if not success:
				sys.exit(1)
			
			# Run in QEMU if requested
			if args.qemu or args.qemu_system:
				qemu_mode = 'system' if args.qemu_system else 'user'
				if not run_qemu(executable_name, args.verbose, qemu_mode, args.qemu_kernel, args.qemu_bios):
					sys.exit(1)
	except Exception as e:
		print(f"Error generating code: {e}", file=sys.stderr)
		import traceback
		traceback.print_exc()
		sys.exit(1)


if __name__ == '__main__':
	main()