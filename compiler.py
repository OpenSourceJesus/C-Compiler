#!/usr/bin/env python3
"""Main compiler entry point."""

import argparse
import sys
import os
from pathlib import Path
from parser import CParser, MultiFileParser, find_c_files
from analyzer import analyze_all_functions, analyze_global_variables
from codegen import CodeGenerator


def main():
    """Main compiler entry point."""
    parser = argparse.ArgumentParser(description='Custom C Compiler with Function Call Optimizations')
    parser.add_argument('input_path', help='Input C source file or directory containing C files')
    parser.add_argument('-o', '--output', help='Output assembly file', default=None)
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    input_path = Path(args.input_path)
    
    # Determine if input is a file or directory
    if input_path.is_file():
        # Single file mode
        c_files = [str(input_path)]
        c_parser = CParser()
        try:
            ast = c_parser.parse_file(args.input_path)
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
    
    # Generate code
    try:
        codegen = CodeGenerator(function_data, global_var_data)
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
    except Exception as e:
        print(f"Error generating code: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()