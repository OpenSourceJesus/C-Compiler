"""Collect symbols (functions and globals) referenced in C code."""

from pycparser import c_ast


class SymbolCollector(c_ast.NodeVisitor):
    """Visitor to collect all function calls and global variable references."""
    
    def __init__(self):
        self.referenced_functions = set()  # Functions called
        self.referenced_globals = set()  # Global variables accessed
        self.declared_functions = set()  # Functions defined
        self.declared_globals = set()  # Global variables defined
    
    def visit_FuncCall(self, node):
        """Collect function calls."""
        if isinstance(node.name, c_ast.ID):
            func_name = node.name.name
            self.referenced_functions.add(func_name)
        elif isinstance(node.name, c_ast.UnaryOp) and isinstance(node.name.expr, c_ast.ID):
            # Function pointer: (*func_ptr)()
            func_name = node.name.expr.name
            self.referenced_functions.add(func_name)
        self.generic_visit(node)
    
    def visit_FuncDef(self, node):
        """Collect function definitions."""
        if node.decl and node.decl.name:
            self.declared_functions.add(node.decl.name)
        self.generic_visit(node)
    
    def visit_Decl(self, node):
        """Collect global variable declarations and references."""
        if node.name:
            # Check if it's a function declaration
            if isinstance(node.type, c_ast.FuncDecl):
                # External function declaration
                self.referenced_functions.add(node.name)
            else:
                # Variable declaration
                # Check if it's global (not inside a function)
                if not getattr(self, '_in_function', False):
                    self.declared_globals.add(node.name)
                else:
                    # Local variable - might reference a global
                    pass
        self.generic_visit(node)
    
    def visit_ID(self, node):
        """Collect ID references (could be global variables)."""
        # We'll check if this is a global in the expression context
        # This is a simplified approach - in practice, we'd need more context
        self.generic_visit(node)
    
    def visit_FuncDef(self, node):
        """Mark that we're entering a function."""
        old_in_function = getattr(self, '_in_function', False)
        self._in_function = True
        if node.decl and node.decl.name:
            self.declared_functions.add(node.decl.name)
        self.generic_visit(node)
        self._in_function = old_in_function
    
    def get_external_symbols(self):
        """Get symbols that are referenced but not defined in C code."""
        external_functions = self.referenced_functions - self.declared_functions
        # For globals, we assume all referenced IDs might be external
        # This is simplified - a real implementation would track which are actually globals
        return {
            'functions': external_functions,
            'globals': self.referenced_globals - self.declared_globals
        }


def collect_symbols(parser):
    """Collect all symbols referenced in parsed C code.
    
    Args:
        parser: CParser or MultiFileParser instance
        
    Returns:
        dict with 'functions' and 'globals' sets
    """
    collector = SymbolCollector()
    
    # Visit all functions
    functions = parser.get_functions()
    for func in functions:
        collector.visit(func)
    
    # Visit all global variables
    globals = parser.get_global_variables()
    for gvar in globals:
        collector.visit(gvar)
    
    # Also visit the AST root to catch any top-level references
    if hasattr(parser, 'ast') and parser.ast:
        collector.visit(parser.ast)
    elif hasattr(parser, 'parsers'):
        # MultiFileParser - visit each parser's AST
        for p in parser.parsers:
            if hasattr(p, 'ast') and p.ast:
                collector.visit(p.ast)
    
    return collector.get_external_symbols()
