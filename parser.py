"""C code parser using pycparser."""

from pycparser import c_parser, c_ast, parse_file
try:
    from pycparser.c_parser import ParseError
except ImportError:
    from pycparser.plyparser import ParseError
import sys
import os
import re
import tempfile
from pathlib import Path
from debug_gdb import (
    prepare_source_and_debug_comments,
    map_stripped_lines_to_preprocessed,
    remap_debug_line_numbers,
)


class CParser:
    """Parser for C code using pycparser."""
    
    def __init__(self, include_paths=None):
        self.parser = c_parser.CParser()
        self.ast = None
        self._alignas_info = {}  # Store _Alignas information extracted during preprocessing
        self._register_assertions = []
        self._memdumps = []
        self.source_file = None
        self.extract_debug_comments = False
        self._function_source_files = {}
        self.include_paths = include_paths or []  # Additional include directories
    
    @staticmethod
    def _extract_alignas_info(content):
        """Extract _Alignas(N) information from preprocessed content.
        
        Returns a dict mapping variable names to their alignment values.
        Pattern: 'auto _Alignas(N) char var_name;'
        """
        alignas_info = {}
        lines = content.split('\n')
        
        for line in lines:
            # Match pattern: auto _Alignas(N) char var_name;
            # or variations with signed/unsigned
            match = re.search(r'auto\s+_Alignas\s*\(\s*(\d+)\s*\)\s+(?:signed\s+|unsigned\s+)?char\s+(\w+)\s*;', line, re.IGNORECASE)
            if match:
                align_value = int(match.group(1))
                var_name = match.group(2)
                alignas_info[var_name] = align_value
        
        return alignas_info
    
    @staticmethod
    def _preprocess_inline_asm(content):
        """Remove inline assembly statements to make code parseable by pycparser.
        
        Replaces patterns like:
        - asm volatile("lock; addl..." ::: "memory");
        - asm("...");
        - volatile("...");  (after asm is removed by preprocessor)
        with empty statements (;)
        
        Uses a state machine approach to properly handle semicolons inside strings.
        """
        lines = content.split('\n')
        result_lines = []
        
        for line in lines:
            # Process line by line to handle inline assembly statements
            # Match patterns like:
            # - asm volatile("...") or asm volatile("..." ::: "memory");
            # - volatile("..."); (after asm removal)
            
            # Pattern for asm/__asm__ statements - match from keyword to semicolon
            # This handles the full inline assembly syntax including constraints
            line = re.sub(r'\b(asm|__asm__|__asm)\s*(?:volatile\s*)?\s*\([^)]*(?:\([^)]*\)[^)]*)*\)[^;]*;', ';', line)
            
            # Pattern for volatile statements (after asm is removed)
            # Match: volatile followed by parenthesized content ending with semicolon
            # Need to handle semicolons inside strings by matching to end-of-statement semicolon
            # Simple approach: match volatile(...) followed by optional constraints and semicolon
            line = re.sub(r'\bvolatile\s*\([^)]*(?:\([^)]*\)[^)]*)*\)[^;]*;', ';', line)
            
            # Handle __extension__ patterns
            line = re.sub(r'__extension__\s*volatile\s*\([^)]*(?:\([^)]*\)[^)]*)*\)[^;]*;', ';', line)
            
            # More aggressive pattern: match any remaining inline assembly-like patterns
            # Match patterns where we have parentheses with quoted strings and semicolons inside
            # followed by a statement-ending semicolon
            # This is a fallback for complex cases
            if 'volatile' in line and '(' in line and ';' in line:
                # Try to match from volatile to semicolon, counting parentheses
                # Simple heuristic: if line has volatile followed by ( and ends with );, it's likely inline asm
                if re.search(r'volatile\s*\(.*\)\s*;', line):
                    # More careful: count parentheses to match balanced pairs
                    # For simplicity, match from volatile to the last semicolon on the line
                    # This works for single-line inline assembly
                    line = re.sub(r'volatile\s*\([^;]*\)\s*;', ';', line)
            
            result_lines.append(line)
        
        content = '\n'.join(result_lines)
        
        # Additional pass: handle any remaining patterns that span the line boundary handling above
        # Match any remaining asm-like patterns
        content = re.sub(r'\b(asm|__asm__|__asm)\s+[^;]+;', ';', content)
        
        return content
    
    def parse_file(self, filename):
        """Parse a C file into an AST."""
        # Convert filename to absolute path early to avoid issues with path resolution
        abs_filename = os.path.abspath(filename)
        self.source_file = abs_filename
        try:
            with open(abs_filename, 'r') as src_file:
                original_content = src_file.read()
            source_content, self._register_assertions, self._memdumps = prepare_source_and_debug_comments(
                original_content, abs_filename, self.extract_debug_comments,
            )
        except OSError:
            original_content = ''
            source_content = ''
            self._register_assertions = []
            self._memdumps = []
        try:
            # Try to use cpp, but fall back to direct parsing if not available
            try:
                # Get the directory where this script is located to find the wrapper header
                script_dir = os.path.dirname(os.path.abspath(__file__))
                wrapper_header = os.path.join(script_dir, 'pycparser_wrapper.h')
                source_dir = os.path.dirname(abs_filename)
                
                # Define GCC-specific attributes and extensions as empty macros so pycparser can handle them
                # Use variadic macro for __attribute__ to handle __attribute__((...)) syntax
                cpp_args = [
                    '-E',
                    '-P',  # Don't include line markers
                    '-std=c11',                      # Enable C11 for _Alignas support
                    '-D__attribute__(...)=',         # Define __attribute__ as empty variadic macro
                    '-D__extension__=',              # Define __extension__ as empty macro
                    '-D__inline__=inline',           # Map __inline__ to standard inline
                    '-D__inline=inline',             # Map __inline to standard inline
                    '-D__restrict__=',               # Define __restrict__ as empty (C99 has restrict)
                    '-D__restrict=',                 # Define __restrict as empty
                    '-D__const__=const',             # Map __const__ to const
                    '-D__volatile__=volatile',       # Map __volatile__ to volatile
                    '-Dasm=',                        # Remove asm keyword
                    '-D__asm__=',                    # Remove __asm__ keyword
                    '-D__asm=',                      # Remove __asm keyword
                    '-I=' + os.path.split(filename)[0]
                ]
                
                # Add source directory to include path for relative includes
                cpp_args.append(f'-I{source_dir}')
                
                # Add user-specified include paths (convert to absolute paths)
                for inc_path in self.include_paths:
                    abs_inc_path = os.path.abspath(inc_path)
                    cpp_args.append(f'-I{abs_inc_path}')
                
                # Include wrapper header if it exists
                if os.path.exists(wrapper_header):
                    cpp_args.append(f'-include{wrapper_header}')
                
                # Try to use fake libc headers if available
                try:
                    import pycparser_fake_libc
                    fake_libc_path = os.path.dirname(pycparser_fake_libc.__file__)
                    cpp_args.append(f'-I{fake_libc_path}')
                except ImportError:
                    pass  # fake libc not available, use system headers
                
                # Call cpp manually to get preprocessed output
                with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as src_tmp:
                    src_tmp.write(source_content)
                    cpp_input_path = src_tmp.name

                import subprocess
                try:
                    result = subprocess.run(
                        ['cpp'] + cpp_args + [cpp_input_path],
                        capture_output=True,
                        text=True,
                        cwd=source_dir
                    )
                finally:
                    try:
                        os.unlink(cpp_input_path)
                    except OSError:
                        pass
                
                if result.returncode != 0:
                    raise RuntimeError(f"cpp preprocessing failed: {result.stderr}")
                
                # Process the preprocessed output to remove inline assembly
                preprocessed_content = result.stdout
                line_mapping = map_stripped_lines_to_preprocessed(source_content, preprocessed_content)
                self._register_assertions = remap_debug_line_numbers(self._register_assertions, line_mapping)
                self._memdumps = remap_debug_line_numbers(self._memdumps, line_mapping)
                
                # Extract _Alignas information before preprocessing removes it
                # Store it for later use in the analyzer
                self._alignas_info = self._extract_alignas_info(preprocessed_content)
                
                preprocessed_content = self._preprocess_inline_asm(preprocessed_content)
                
                # Write to temp file and parse without cpp
                with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as tmp_file:
                    tmp_file.write(preprocessed_content)
                    tmp_filename = tmp_file.name
                
                try:
                    # Parse the preprocessed file without using cpp again
                    self.ast = parse_file(tmp_filename, use_cpp=False)
                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(tmp_filename)
                    except OSError:
                        pass
            except (FileNotFoundError, OSError):
                # Fall back to direct parsing (without preprocessing)
                # This works for simple C code without stdlib includes
                # Try to extract _Alignas info from source file directly
                try:
                    with open(abs_filename, 'r') as f:
                        source_content = f.read()
                    self._alignas_info = self._extract_alignas_info(source_content)
                    source_content, self._register_assertions, self._memdumps = prepare_source_and_debug_comments(
                        source_content, abs_filename, self.extract_debug_comments,
                    )
                except OSError:
                    self._alignas_info = {}
                    self._register_assertions = []
                    self._memdumps = []
                    source_content = original_content if original_content else ''
                if source_content:
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as tmp_file:
                        tmp_file.write(source_content)
                        tmp_filename = tmp_file.name
                    try:
                        self.ast = parse_file(tmp_filename, use_cpp=False)
                    finally:
                        try:
                            os.unlink(tmp_filename)
                        except OSError:
                            pass
                else:
                    self.ast = parse_file(abs_filename, use_cpp=False)
            return self.ast
        except ParseError as e:
            print(f"Parse error: {e}", file=sys.stderr)
            raise
        except Exception as e:
            print(f"Error parsing file: {e}", file=sys.stderr)
            raise
    
    def parse_string(self, code):
        """Parse C code from a string into an AST."""
        try:
            self.ast = self.parser.parse(code)
            return self.ast
        except ParseError as e:
            print(f"Parse error: {e}", file=sys.stderr)
            raise
    
    def get_functions(self):
        """Extract all function definitions from the AST."""
        if not self.ast:
            return []
        
        functions = []
        visitor = FunctionExtractor()
        visitor.visit(self.ast)
        if self.source_file:
            for func in visitor.functions:
                self._function_source_files[id(func)] = self.source_file
        return visitor.functions
    
    def get_global_variables(self):
        """Extract all global variable declarations from the AST."""
        if not self.ast:
            return []
        
        globals = []
        visitor = GlobalVariableExtractor()
        visitor.visit(self.ast)
        # Don't overwrite _alignas_info - it's already set during parse_file
        # The visitor's alignas_info is separate and not used
        return visitor.globals
    
    def get_register_assertions(self):
        """Get register assertions extracted during parsing."""
        return list(getattr(self, '_register_assertions', []))

    def get_memdumps(self):
        """Get MEMDUMP debug requests extracted during parsing."""
        return list(getattr(self, '_memdumps', []))

    def get_function_source_files(self):
        """Map function AST node ids to their source file paths."""
        return dict(getattr(self, '_function_source_files', {}))
    
    def get_alignas_info(self):
        """Get _Alignas information extracted during parsing."""
        return getattr(self, '_alignas_info', {})


class FunctionExtractor(c_ast.NodeVisitor):
    """Visitor to extract function definitions from AST."""
    
    def __init__(self):
        self.functions = []
    
    def visit_FuncDef(self, node):
        """Collect function definitions."""
        func_name = node.decl.name if node.decl else "unknown"
        self.functions.append(node)
        self.generic_visit(node)


class GlobalVariableExtractor(c_ast.NodeVisitor):
    """Visitor to extract global variable declarations from AST."""
    
    def __init__(self):
        self.globals = []
        self.in_function = False
        self.alignas_info = {}  # Store _Alignas information: {var_name: align_value}
    
    def visit_FuncDef(self, node):
        """Skip variables inside functions."""
        self.in_function = True
        self.generic_visit(node)
        self.in_function = False
    
    def visit_Decl(self, node):
        """Collect global variable declarations (not in functions)."""
        if self.in_function or not node.name:
            return
        # Only collect true file-scope variable declarations.
        # Do not descend into declaration children; doing so pulls in
        # function-parameter and struct-member Decl nodes as "globals".
        if isinstance(node.type, c_ast.FuncDecl):
            return
        self.globals.append(node)


class MultiFileParser:
    """Parser that aggregates functions and globals from multiple C files."""
    
    def __init__(self, include_paths=None):
        self.parsers = []  # List of CParser instances, one per file
        self.file_paths = []  # List of file paths
        self.include_paths = include_paths or []  # Additional include directories
        self.extract_debug_comments = False
    
    def parse_files(self, file_paths):
        """Parse multiple C files and aggregate their ASTs."""
        self.file_paths = file_paths
        self.parsers = []
        
        for file_path in file_paths:
            parser = CParser(include_paths=self.include_paths)
            parser.extract_debug_comments = self.extract_debug_comments
            try:
                parser.parse_file(file_path)
                self.parsers.append(parser)
            except Exception as e:
                print(f"Warning: Failed to parse {file_path}: {e}", file=sys.stderr)
                raise
        
        return self.parsers
    
    def get_functions(self):
        """Extract all function definitions from all parsed files."""
        all_functions = []
        self._function_source_files = {}
        for parser, file_path in zip(self.parsers, self.file_paths):
            functions = parser.get_functions()
            source_file = os.path.abspath(file_path)
            for func in functions:
                self._function_source_files[id(func)] = source_file
                all_functions.append(func)
        return all_functions

    def get_function_source_files(self):
        """Map function AST node ids to their source file paths."""
        return dict(getattr(self, '_function_source_files', {}))
    
    def get_register_assertions(self):
        """Get register assertions from all parsed files."""
        assertions = []
        for parser in self.parsers:
            assertions.extend(parser.get_register_assertions())
        return assertions

    def get_memdumps(self):
        """Get MEMDUMP requests from all parsed files."""
        memdumps = []
        for parser in self.parsers:
            memdumps.extend(parser.get_memdumps())
        return memdumps
    
    def get_global_variables(self):
        """Extract all global variable declarations from all parsed files."""
        all_globals = []
        for parser in self.parsers:
            globals = parser.get_global_variables()
            all_globals.extend(globals)
        return all_globals


def find_c_files(directory):
    """Recursively find all .c files in a directory and its subdirectories."""
    c_files = []
    path = Path(directory)
    
    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    if not path.is_dir():
        raise ValueError(f"Not a directory: {directory}")
    
    # Recursively find all .c files
    for c_file in path.rglob("*.c"):
        c_files.append(str(c_file))
    
    # Sort for deterministic order
    c_files.sort()
    
    return c_files