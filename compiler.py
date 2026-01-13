#!/usr/bin/env python3
"""Main compiler entry point."""

import argparse
import sys
from parser import CParser
from analyzer import analyze_all_functions
from codegen import CodeGenerator


def main():
    """Main compiler entry point."""
    parser = argparse.ArgumentParser(description='Custom C Compiler with Function Call Optimizations')
    parser.add_argument('input_file', help='Input C source file')
    parser.add_argument('-o', '--output', help='Output assembly file', default=None)
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Parse input file
    c_parser = CParser()
    try:
        ast = c_parser.parse_file(args.input_file)
        if args.verbose:
            print(f"Parsed {args.input_file} successfully", file=sys.stderr)
    except Exception as e:
        print(f"Error parsing {args.input_file}: {e}", file=sys.stderr)
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
    
    # Generate code
    try:
        codegen = CodeGenerator(function_data)
        output_code = codegen.generate(c_parser)
        
        # Write output
        output_file = args.output or args.input_file.replace('.c', '.asm')
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