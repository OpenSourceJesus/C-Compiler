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
        self.packed_vars = []  # Variables that can be packed (1-8 bits)
        self.bit_positions = {}  # Map variable name to (start_bit, bit_width)
        self.current_bit = 0
        self.simd_register_size = 128  # xmm15 is 128-bit, can use ymm15/zmm15 for wider
        self.alignas_info = {}  # _Alignas information from parser: {var_name: align_value}
    
    def get_type_bits(self, decl):
        """Determine the bit width of a variable type.
        
        Detects 1-8 bit types for SIMD packing using _Alignas(N) convention:
        - 'auto _Alignas(N) char' indicates an N-bit variable (N = 1-8)
        - Only applies to 'char', 'signed char', or 'unsigned char' types
        - Requires 'auto' storage class
        """
        if not decl or not decl.type:
            return None
        
        type_str = self._type_to_string(decl.type)
        var_name = decl.name if decl.name else ""
        type_lower = type_str.lower()
        
        # Check for _Alignas(N) convention: 'auto _Alignas(N) char'
        # First, verify it's a char type (char, signed char, or unsigned char)
        is_char_type = any(char_type in type_lower for char_type in ['char', 'signed char', 'unsigned char'])
        
        if is_char_type:
            # First check if we have _Alignas info from the parser (extracted from preprocessed source)
            # If _Alignas info exists, it means the variable was declared with 'auto _Alignas(N) char'
            # so we can trust that 'auto' was present in the original source
            if var_name in self.alignas_info:
                align_value = self.alignas_info[var_name]
                if 1 <= align_value <= 8:
                    # Since we extracted this from 'auto _Alignas(N) char' pattern,
                    # we know 'auto' was present in the original declaration
                    # (the extraction function only matches patterns with 'auto')
                    return align_value
            
            # Fallback: Check for _Alignas(N) in multiple places:
            # 1. In the type string (after preprocessing)
            # 2. In type qualifiers
            # 3. In alignment attributes
            
            align_value = None
            
            # Check type string for _Alignas(N) pattern
            alignas_match = re.search(r'_alignas\s*\(\s*(\d+)\s*\)', type_lower, re.IGNORECASE)
            if alignas_match:
                align_value = int(alignas_match.group(1))
            
            # Check type qualifiers if not found in string
            if align_value is None and isinstance(decl.type, c_ast.TypeDecl):
                if hasattr(decl.type, 'quals') and decl.type.quals:
                    quals_str = ' '.join(decl.type.quals).lower()
                    alignas_match = re.search(r'_alignas\s*\(\s*(\d+)\s*\)', quals_str, re.IGNORECASE)
                    if alignas_match:
                        align_value = int(alignas_match.group(1))
            
            # Check for alignment attribute (if pycparser stores it separately)
            if align_value is None and isinstance(decl.type, c_ast.TypeDecl):
                # Check if there's an alignment attribute
                if hasattr(decl.type, 'alignment') and decl.type.alignment:
                    # Try to extract numeric value from alignment
                    try:
                        if isinstance(decl.type.alignment, c_ast.Constant):
                            align_value = int(decl.type.alignment.value)
                        elif hasattr(decl.type.alignment, 'value'):
                            align_value = int(decl.type.alignment.value)
                    except:
                        pass
            
            if align_value is not None and 1 <= align_value <= 8:
                # Verify 'auto' storage class is present
                has_auto = 'auto' in type_lower
                # Check declarator storage if available
                if not has_auto and hasattr(decl, 'storage') and decl.storage:
                    if isinstance(decl.storage, list):
                        has_auto = 'auto' in [s.lower() for s in decl.storage]
                    elif isinstance(decl.storage, str):
                        has_auto = 'auto' in decl.storage.lower()
                
                # Also check if 'auto' appears before the type in the full declaration
                # This handles cases where preprocessor expands macros
                if not has_auto:
                    # Try to get the full source representation if available
                    full_type_str = str(decl.type) if hasattr(decl, 'type') else type_str
                    has_auto = 'auto' in full_type_str.lower()
                
                if has_auto:
                    print(f"{var_name} has bit-width {align_value} from _Alignas({align_value}) char with auto storage")
                    return align_value
        
        # Legacy support: Check for bit-width in variable name (e.g., flag_1bit, counter_3bit)
        # This is deprecated in favor of _Alignas convention
        name_bit_match = re.search(r'_(\d+)bit', var_name.lower())
        if name_bit_match:
            bits = int(name_bit_match.group(1))
            if 1 <= bits <= 8:
                return bits
        
        # Check for bit-field declarations (e.g., int flag : 1)
        # Note: Requires C preprocessing for full support
        if isinstance(decl.type, c_ast.TypeDecl):
            # Check if there's a bitfield width in the declarator
            if hasattr(decl, 'bitsize') and decl.bitsize:
                try:
                    bits = int(decl.bitsize.value)
                    if 1 <= bits <= 8:
                        return bits
                except:
                    pass
        
        # Check for custom bit-width types (e.g., int1_t, uint3_t, etc.)
        bit_match = re.search(r'(\d+)_t$', type_lower)
        if bit_match:
            bits = int(bit_match.group(1))
            if 1 <= bits <= 8:
                return bits
        
        # Default: use standard type sizes, but only pack if <= 8 bits
        # Note: Standard types are typically >= 8 bits, so this rarely applies
        base_bits = self.TYPE_BITS.get(type_lower, 32)
        if base_bits <= 8:
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
            
            # Combine qualifiers and type name
            result = ' '.join(quals + [type_name])
            return result
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
            if bits and 1 <= bits <= 8:
                # Check if it fits in the SIMD register (up to 128 bits total)
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
    # Get _Alignas information from parser
    if hasattr(parser, 'get_alignas_info'):
        alignas_info = parser.get_alignas_info()
    elif hasattr(parser, '_alignas_info'):
        alignas_info = parser._alignas_info
    else:
        alignas_info = {}
    analyzer.alignas_info = alignas_info
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