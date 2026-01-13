"""Function analysis for size calculation and return site detection."""

from pycparser import c_ast
import re


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


class GlobalVariableAnalyzer:
    """Analyzer for global variables to determine bit-width and SIMD packing."""
    
    # Type to bit-width mapping
    TYPE_BITS = {
        'char': 8,
        'signed char': 8,
        'unsigned char': 8,
        'short': 16,
        'signed short': 16,
        'unsigned short': 16,
        'int': 32,
        'signed int': 32,
        'unsigned int': 32,
        'long': 64,
        'signed long': 64,
        'unsigned long': 64,
        'long long': 64,
        'signed long long': 64,
        'unsigned long long': 64,
    }
    
    def __init__(self):
        self.packed_vars = []  # Variables that can be packed (1-7 bits)
        self.bit_positions = {}  # Map variable name to (start_bit, bit_width)
        self.current_bit = 0
        self.simd_register_size = 128  # xmm15 is 128-bit, can use ymm15/zmm15 for wider
    
    def get_type_bits(self, decl):
        """Determine the bit width of a variable type.
        
        Detects 1-7 bit types for SIMD packing:
        - Bit-fields (requires preprocessing support)
        - Custom bit-width types (int1_t, uint3_t, etc.)
        - Variables with bit-width in name (flag_1bit, counter_5bit)
        - Small standard types that fit in 1-7 bits
        """
        if not decl or not decl.type:
            return None
        
        type_str = self._type_to_string(decl.type)
        var_name = decl.name if decl.name else ""
        
        # Check for bit-width in variable name (e.g., flag_1bit, counter_3bit)
        name_bit_match = re.search(r'_(\d+)bit', var_name.lower())
        if name_bit_match:
            bits = int(name_bit_match.group(1))
            if 1 <= bits <= 7:
                return bits
        
        # Check for bit-field declarations (e.g., int flag : 1)
        # Note: Requires C preprocessing for full support
        if isinstance(decl.type, c_ast.TypeDecl):
            # Check if there's a bitfield width in the declarator
            if hasattr(decl, 'bitsize') and decl.bitsize:
                try:
                    bits = int(decl.bitsize.value)
                    if 1 <= bits <= 7:
                        return bits
                except:
                    pass
        
        # Check for explicit bit-width annotations in comments or attributes
        type_lower = type_str.lower()
        
        # Check for custom bit-width types (e.g., int1_t, uint3_t, etc.)
        bit_match = re.search(r'(\d+)_t$', type_lower)
        if bit_match:
            bits = int(bit_match.group(1))
            if 1 <= bits <= 7:
                return bits
        
        # Default: use standard type sizes, but only pack if <= 7 bits
        base_bits = self.TYPE_BITS.get(type_lower, 32)
        if base_bits <= 7:
            return base_bits
        
        return None
    
    def _type_to_string(self, type_node):
        """Convert type node to string representation."""
        if isinstance(type_node, c_ast.TypeDecl):
            quals = []
            if type_node.quals:
                quals.extend(type_node.quals)
            
            type_name = 'int'  # default
            if isinstance(type_node.type, c_ast.IdentifierType):
                names = type_node.type.names
                if names:
                    type_name = ' '.join(names)
            
            return ' '.join(quals + [type_name])
        elif isinstance(type_node, c_ast.IdentifierType):
            return ' '.join(type_node.names) if type_node.names else 'int'
        else:
            return 'int'
    
    def analyze_globals(self, global_vars):
        """Analyze global variables and determine which can be packed."""
        self.packed_vars = []
        self.bit_positions = {}
        self.current_bit = 0
        
        for var in global_vars:
            var_name = var.name if var.name else None
            if not var_name:
                continue
            
            bits = self.get_type_bits(var)
            if bits and 1 <= bits <= 7:
                # Check if it fits in the SIMD register
                if self.current_bit + bits <= self.simd_register_size:
                    self.packed_vars.append({
                        'name': var_name,
                        'bits': bits,
                        'node': var,
                        'start_bit': self.current_bit
                    })
                    self.bit_positions[var_name] = (self.current_bit, bits)
                    self.current_bit += bits
                else:
                    # Register is full, can't pack more
                    break
        
        return {
            'packed_vars': self.packed_vars,
            'bit_positions': self.bit_positions,
            'total_bits_used': self.current_bit
        }


def analyze_global_variables(parser):
    """Analyze global variables for SIMD bit-packing."""
    globals = parser.get_global_variables()
    analyzer = GlobalVariableAnalyzer()
    return analyzer.analyze_globals(globals)


def is_interrupt_callback(func_name):
    """Determine if a function is an interrupt callback."""
    # Common interrupt callback naming patterns
    interrupt_patterns = [
        r'^isr_',  # Interrupt Service Routine
        r'^irq_',  # IRQ handler
        r'^interrupt_',  # Generic interrupt
        r'_handler$',  # Handler suffix
        r'_callback$',  # Callback suffix
        r'^__attribute__.*interrupt',  # GCC interrupt attribute
    ]
    
    for pattern in interrupt_patterns:
        if re.search(pattern, func_name, re.IGNORECASE):
            return True
    
    return False