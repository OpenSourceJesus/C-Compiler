"""C code parser using pycparser."""

from pycparser import c_parser, c_ast, parse_file
from pycparser.plyparser import ParseError
import sys
import os
from pathlib import Path


class CParser:
    """Parser for C code using pycparser."""
    
    def __init__(self):
        self.parser = c_parser.CParser()
        self.ast = None
    
    def parse_file(self, filename):
        """Parse a C file into an AST."""
        try:
            # Try to use cpp, but fall back to direct parsing if not available
            try:
                # Try with cpp preprocessing
                self.ast = parse_file(filename, use_cpp=True,
                                     cpp_path='cpp',
                                     cpp_args=['-E'])
            except (FileNotFoundError, OSError):
                # Fall back to direct parsing (without preprocessing)
                # This works for simple C code without stdlib includes
                self.ast = parse_file(filename, use_cpp=False)
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
        return visitor.functions
    
    def get_global_variables(self):
        """Extract all global variable declarations from the AST."""
        if not self.ast:
            return []
        
        globals = []
        visitor = GlobalVariableExtractor()
        visitor.visit(self.ast)
        return visitor.globals


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
    
    def visit_FuncDef(self, node):
        """Skip variables inside functions."""
        self.in_function = True
        self.generic_visit(node)
        self.in_function = False
    
    def visit_Decl(self, node):
        """Collect global variable declarations (not in functions)."""
        if not self.in_function and node.name:
            # Check if it's a variable (not a function)
            if not isinstance(node.type, c_ast.FuncDecl):
                self.globals.append(node)
        self.generic_visit(node)


class MultiFileParser:
    """Parser that aggregates functions and globals from multiple C files."""
    
    def __init__(self):
        self.parsers = []  # List of CParser instances, one per file
        self.file_paths = []  # List of file paths
    
    def parse_files(self, file_paths):
        """Parse multiple C files and aggregate their ASTs."""
        self.file_paths = file_paths
        self.parsers = []
        
        for file_path in file_paths:
            parser = CParser()
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
        for parser in self.parsers:
            functions = parser.get_functions()
            all_functions.extend(functions)
        return all_functions
    
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