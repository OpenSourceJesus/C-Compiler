"""C code parser using pycparser."""

from pycparser import c_parser, c_ast, parse_file
from pycparser.plyparser import ParseError
import sys
import os


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