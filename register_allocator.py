"""Register allocator that analyzes call graph and variable usage for efficient register allocation."""

from pycparser import c_ast
from collections import defaultdict
import re


class RegisterAllocator:
    """Analyzes functions and allocates registers to frequently-used variables."""
    
    # Available general-purpose registers (x86-64)
    # We reserve RBP (frame pointer), RSP (stack pointer), RDI/RSI/RDX/RCX (args)
    # Available: RAX, RBX, R8, R9, R10, R11, R12, R13, R14, R15
    # For 64-bit: prefer RAX, RBX, R8, R9, R10, R11 (R12/R13 used for indexed stack)
    # For 32-bit: prefer EAX, EBX, ECX, EDX (but ECX/EDX may be used for args)
    
    def __init__(self, use_32bit=False):
        self.use_32bit = use_32bit
        self.function_register_map = {}  # {func_name: {var_name: register}}
        self.variable_usage = defaultdict(int)  # Track how often variables are accessed
        self.loop_variables = set()  # Variables used in loops (should be in registers)
        self.accumulator_variables = set()  # Variables that accumulate values (sum, product, etc.)
        self.parameter_registers = {}  # Track which parameters stay in their original registers
        
    def analyze_function(self, func_def, parser):
        """Analyze a function to determine register allocation."""
        func_name = func_def.decl.name if func_def.decl else "unknown"
        if func_name == "unknown":
            return
        
        # Reset for this function
        self.variable_usage.clear()
        self.loop_variables.clear()
        self.accumulator_variables.clear()
        
        # Analyze variable usage patterns
        analyzer = VariableUsageAnalyzer()
        analyzer.visit(func_def)
        
        self.variable_usage = analyzer.usage_count
        self.loop_variables = analyzer.loop_vars
        self.accumulator_variables = analyzer.accumulators
        
        # Allocate registers
        register_map = self._allocate_registers(func_name, func_def, parser)
        self.function_register_map[func_name] = register_map
        
        return register_map
    
    def _allocate_registers(self, func_name, func_def, parser):
        """Allocate registers to variables based on usage patterns."""
        register_map = {}
        
        # Priority order for register allocation:
        # 1. Loop counters (highest priority - used every iteration)
        # 2. Accumulators (sum, product, etc. - modified frequently)
        # 3. Frequently accessed variables (used multiple times)
        # 4. Function parameters (keep in original registers when possible)
        
        # Available registers (in order of preference)
        # For loop variables and accumulators, prefer registers other than RAX
        # since RAX is heavily used for expression evaluation
        if self.use_32bit:
            available_regs = ['EBX', 'ECX', 'EDX', 'EAX']  # EBP/ESP reserved, EDI/ESI for args
        else:
            # Reserve RBP, RSP, RDI, RSI, RDX, RCX for frame pointer, stack, and args
            # For loop variables: prefer R8, R9, R10, R11, RBX (avoid RAX which is used for expressions)
            # R12/R13 are used for indexed stack system
            # Use RBX, R8, R9, R10, R11, RAX (RAX last since it's used for expressions)
            available_regs = ['RBX', 'R8', 'R9', 'R10', 'R11', 'RAX']
        
        reg_index = 0
        
        # 1. Allocate loop counters first
        for var_name in sorted(self.loop_variables, key=lambda v: self.variable_usage.get(v, 0), reverse=True):
            if reg_index < len(available_regs):
                register_map[var_name] = available_regs[reg_index]
                reg_index += 1
        
        # 2. Allocate accumulators
        for var_name in sorted(self.accumulator_variables, key=lambda v: self.variable_usage.get(v, 0), reverse=True):
            if var_name not in register_map and reg_index < len(available_regs):
                register_map[var_name] = available_regs[reg_index]
                reg_index += 1
        
        # 3. Allocate frequently accessed variables (used 3+ times)
        for var_name, count in sorted(self.variable_usage.items(), key=lambda x: x[1], reverse=True):
            if var_name not in register_map and count >= 3 and reg_index < len(available_regs):
                # Skip if it's a large array (should stay on stack)
                if not self._is_large_array(var_name, func_def, parser):
                    register_map[var_name] = available_regs[reg_index]
                    reg_index += 1
        
        # 4. Function parameters: keep in original registers when possible
        # Parameters are already in RDI, RSI, RDX, RCX, R8, R9
        # We can keep them there if they're used frequently
        param_regs = ['RDI', 'RSI', 'RDX', 'RCX', 'R8', 'R9'] if not self.use_32bit else ['EDI', 'ESI', 'EDX', 'ECX']
        param_index = 0
        if func_def.decl and func_def.decl.type:
            # Extract parameter names
            params = self._extract_parameters(func_def)
            for param_name in params:
                if param_name in self.variable_usage and self.variable_usage[param_name] >= 2:
                    if param_index < len(param_regs):
                        # Keep parameter in its original register
                        register_map[param_name] = param_regs[param_index]
                        param_index += 1
        
        return register_map
    
    def _is_large_array(self, var_name, func_def, parser):
        """Check if a variable is a large array (should stay on stack)."""
        # Check if it's declared as an array with size > 16 elements
        # This is a heuristic - arrays larger than 16 ints (64 bytes) should stay on stack
        if func_def.body:
            for item in func_def.body.block_items or []:
                if isinstance(item, c_ast.Decl) and item.name:
                    decl_name = item.name.name if isinstance(item.name, c_ast.ID) else str(item.name)
                    if decl_name == var_name:
                        # Check if it's an array
                        type_node = item.type
                        while hasattr(type_node, 'type'):
                            if isinstance(type_node, c_ast.ArrayDecl):
                                # Check array size
                                if hasattr(type_node, 'dim') and type_node.dim:
                                    try:
                                        size = int(type_node.dim.value) if isinstance(type_node.dim, c_ast.Constant) else 0
                                        if size > 16:
                                            return True
                                    except:
                                        pass
                                return False  # Array but size unknown or small
                            type_node = type_node.type
        return False
    
    def _extract_parameters(self, func_def):
        """Extract parameter names from function definition."""
        params = []
        if func_def.decl and func_def.decl.type:
            type_node = func_def.decl.type
            while hasattr(type_node, 'type'):
                if isinstance(type_node, c_ast.FuncDecl):
                    if type_node.args:
                        for param in type_node.args.params or []:
                            if isinstance(param, c_ast.Decl) and param.name:
                                param_name = param.name.name if isinstance(param.name, c_ast.ID) else str(param.name)
                                if param_name:
                                    params.append(param_name)
                    break
                type_node = type_node.type
        return params
    
    def get_register(self, func_name, var_name):
        """Get the register allocated to a variable, or None if it's on the stack."""
        if func_name in self.function_register_map:
            return self.function_register_map[func_name].get(var_name)
        return None
    
    def is_in_register(self, func_name, var_name):
        """Check if a variable is allocated to a register."""
        return self.get_register(func_name, var_name) is not None


class VariableUsageAnalyzer(c_ast.NodeVisitor):
    """Analyzes variable usage patterns to identify candidates for register allocation."""
    
    def __init__(self):
        self.usage_count = defaultdict(int)
        self.loop_vars = set()
        self.accumulators = set()
        self.current_loop_vars = set()  # Variables used in current loop
        self.in_loop = False
        self.in_assignment = False
        self.assignment_target = None
    
    def visit_For(self, node):
        """Track variables used in for loops."""
        old_in_loop = self.in_loop
        old_loop_vars = self.current_loop_vars.copy()
        self.in_loop = True
        self.current_loop_vars = set()
        
        # Visit init, condition, and increment
        if node.init:
            self.visit(node.init)
        if node.cond:
            self.visit(node.cond)
        if node.next:
            self.visit(node.next)
        
        # Variables used in loop become loop variables
        self.loop_vars.update(self.current_loop_vars)
        
        # Visit loop body
        if node.stmt:
            self.visit(node.stmt)
        
        self.in_loop = old_in_loop
        self.current_loop_vars = old_loop_vars
    
    def visit_While(self, node):
        """Track variables used in while loops."""
        old_in_loop = self.in_loop
        old_loop_vars = self.current_loop_vars.copy()
        self.in_loop = True
        self.current_loop_vars = set()
        
        if node.cond:
            self.visit(node.cond)
        
        self.loop_vars.update(self.current_loop_vars)
        
        if node.stmt:
            self.visit(node.stmt)
        
        self.in_loop = old_in_loop
        self.current_loop_vars = old_loop_vars
    
    def visit_ID(self, node):
        """Track variable usage."""
        var_name = node.name
        self.usage_count[var_name] += 1
        
        if self.in_loop:
            self.current_loop_vars.add(var_name)
    
    def visit_Assignment(self, node):
        """Track accumulator variables (variables that accumulate values)."""
        old_in_assignment = self.in_assignment
        old_target = self.assignment_target
        
        self.in_assignment = True
        if isinstance(node.lvalue, c_ast.ID):
            self.assignment_target = node.lvalue.name
        
        # Check for accumulator patterns: x += y, x = x + y, etc.
        if isinstance(node.lvalue, c_ast.ID):
            var_name = node.lvalue.name
            if node.op in ['+=', '-=', '*=', '/=']:
                # Compound assignment - accumulator pattern
                self.accumulators.add(var_name)
            elif node.op == '=' and isinstance(node.rvalue, c_ast.BinaryOp):
                # Check if it's x = x + y pattern
                if isinstance(node.rvalue.left, c_ast.ID) and node.rvalue.left.name == var_name:
                    if node.rvalue.op in ['+', '-', '*', '/']:
                        self.accumulators.add(var_name)
        
        self.generic_visit(node)
        
        self.in_assignment = old_in_assignment
        self.assignment_target = old_target
    
    def generic_visit(self, node):
        """Default visitor."""
        for c_name, c in node.children():
            self.visit(c)


def analyze_all_functions_for_registers(parser, use_32bit=False):
    """Analyze all functions and create register allocation maps."""
    allocator = RegisterAllocator(use_32bit=use_32bit)
    functions = parser.get_functions()
    
    for func in functions:
        allocator.analyze_function(func, parser)
    
    return allocator
