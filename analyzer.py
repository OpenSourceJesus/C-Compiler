"""Function analysis for size calculation and return site detection."""

from pycparser import c_ast


class FunctionAnalyzer(c_ast.NodeVisitor):
    """Analyzer for C functions to determine size and return sites."""
    
    def __init__(self):
        self.function_info = {}
        self.current_function = None
        self.return_sites = []
        self.instruction_count = 0
    
    def analyze_function(self, func_def):
        """Analyze a function definition."""
        func_name = func_def.decl.name if func_def.decl else "unknown"
        self.current_function = func_name
        self.return_sites = []
        self.instruction_count = 0
        
        if func_def.body:
            self.visit(func_def.body)
        
        # Estimate function size (rough approximation: 8 bytes per instruction)
        # This is a simplification; real analysis would require actual code generation
        estimated_size = self.instruction_count * 8
        
        self.function_info[func_name] = {
            'size': estimated_size,
            'return_sites': len(self.return_sites),
            'is_small': estimated_size < 1024,
            'has_single_return': len(self.return_sites) == 1,
            'node': func_def
        }
        
        return self.function_info[func_name]
    
    def visit_Return(self, node):
        """Count return statements."""
        self.return_sites.append(node.coord if node.coord else "unknown")
        self.instruction_count += 2  # return instruction + cleanup
        self.generic_visit(node)
    
    def visit_If(self, node):
        """Count conditional instructions."""
        self.instruction_count += 3  # cmp, jump
        self.generic_visit(node)
    
    def visit_While(self, node):
        """Count loop instructions."""
        self.instruction_count += 2  # loop setup
        self.generic_visit(node)
    
    def visit_For(self, node):
        """Count for loop instructions."""
        self.instruction_count += 2  # loop setup
        self.generic_visit(node)
    
    def visit_BinaryOp(self, node):
        """Count binary operations."""
        self.instruction_count += 1
        self.generic_visit(node)
    
    def visit_UnaryOp(self, node):
        """Count unary operations."""
        self.instruction_count += 1
        self.generic_visit(node)
    
    def visit_Assignment(self, node):
        """Count assignment operations."""
        self.instruction_count += 1
        self.generic_visit(node)
    
    def visit_FuncCall(self, node):
        """Count function call overhead."""
        self.instruction_count += 3  # call setup
        self.generic_visit(node)
    
    def visit_Decl(self, node):
        """Count variable declarations."""
        if node.init:
            self.instruction_count += 1
        self.generic_visit(node)
    
    def generic_visit(self, node):
        """Default visitor to traverse all nodes."""
        for c_name, c in node.children():
            self.visit(c)


def analyze_all_functions(parser):
    """Analyze all functions from a parser."""
    functions = parser.get_functions()
    analyzer = FunctionAnalyzer()
    
    function_data = {}
    for func in functions:
        info = analyzer.analyze_function(func)
        func_name = func.decl.name if func.decl else "unknown"
        function_data[func_name] = info
    
    return function_data