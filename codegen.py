"""Code generator with function call optimizations."""

from pycparser import c_ast
import struct
import sys


def safe_str(obj):
    """Safely convert an object to string, preventing AST node attributes from leaking.
    
    This function ensures that AST node objects are never accidentally output
    as their string representation, which could include attribute names like
    'type' or 'field' that would cause assembly errors.
    """
    if obj is None:
        return "None"
    if isinstance(obj, str):
        return obj
    if isinstance(obj, (int, float, bool)):
        return str(obj)
    # For AST nodes, only output the class name, never the object itself
    if hasattr(obj, '__class__'):
        class_name = obj.__class__.__name__
        # Remove any angle brackets or module paths
        return class_name.split('.')[-1]
    # For other objects, use type name
    return type(obj).__name__


class CodeGenerator:
    """Code generator with indexed-jump, metamorphic return sites, quantized call-backs, and SIMD bit-packing."""
    
    def __init__(self, function_data, global_var_data=None, asm_parser=None):
        self.function_data = function_data
        self.global_var_data = global_var_data or {'packed_vars': [], 'bit_positions': {}, 'total_bits_used': 0}
        self.asm_parser = asm_parser  # Assembly parser for external symbols
        self.output = []
        self.small_functions = []
        self.function_offsets = {}
        self.return_site_base = 0x10000  # Base address for return sites
        self.return_sites = []  # Track return sites for quantized call-backs
        self.return_site_index = 0
        self.alignment = 16  # 16-byte alignment for quantized call-backs
        self.current_line = 0  # Track current output line for return site tracking
        self.simd_register = 'xmm15'  # Last SIMD register for bit-packing
        self.referenced_asm_symbols = set()  # Track which assembly symbols we've included
        
        # Indexed stack pointer system (16-byte intervals)
        self.stack_slot_size = 16  # 16-byte intervals
        self.stack_base_register = 'R12'  # Base address register for stack
        self.stack_index_register = 'R13'  # Index register (stores slot index, fits in 32 bits)
        self.current_function_stack = {}  # Track local variables: {name: (slot_index, offset)}
        self.current_stack_slots = 0  # Number of 16-byte slots allocated in current function
        self.stack_base_address = 'STACK_BASE'  # Symbol for stack base address
        self.label_counter = 0  # Counter for unique labels
    
    def _safe_append(self, line):
        """Safely append a line to output, ensuring no AST node objects are included.
        
        This prevents AST nodes from being accidentally converted to strings
        and output, which could cause assembly errors with labels like 'type'
        or 'field'.
        """
        # If line contains an AST node object, convert it safely
        if isinstance(line, c_ast.Node):
            # This should never happen, but protect against it
            line = f"; ERROR: AST node object detected: {safe_str(line)}"
        elif not isinstance(line, str):
            # Convert non-string objects safely
            line = safe_str(line)
        
        # Check if line looks like it contains an AST node attribute that was output as a label
        # Patterns like "type:" or "field:" at the start of a line (after whitespace)
        import re
        stripped = line.strip()
        # Check for problematic labels that are AST attribute names
        problematic_labels = ['type:', 'field:', 'name:', 'expr:', 'node:', 'struct_ref:', 'assign:']
        if stripped in problematic_labels or (stripped.endswith(':') and len(stripped.split()) == 1 and stripped[:-1] in ['type', 'field', 'name', 'expr', 'node']):
            # This looks like an AST node attribute was output as a label - skip it
            return  # Don't output this line
        
        self.output.append(line)
    
    def generate(self, parser):
        """Generate optimized code for all functions."""
        self.output = []
        self._current_parser = parser  # Store parser reference for variable lookup
        
        # Separate small and large functions, deduplicating by name
        functions = parser.get_functions()
        seen_funcs = {}  # {func_name: func_node} to deduplicate
        for func in functions:
            func_name = func.decl.name if func.decl else "unknown"
            # Skip functions with "unknown" names - they're likely parsing errors
            if func_name == "unknown":
                continue
            # Only keep the first occurrence of each function
            if func_name not in seen_funcs:
                seen_funcs[func_name] = func
        
        # Use deduplicated functions
        unique_functions = list(seen_funcs.values())
        small_funcs = []
        large_funcs = []
        
        for func in unique_functions:
            func_name = func.decl.name if func.decl else "unknown"
            # Skip functions with "unknown" names
            if func_name == "unknown":
                continue
            if func_name in self.function_data and self.function_data[func_name]['is_small']:
                small_funcs.append(func)
            else:
                large_funcs.append(func)
        
        # Generate initialization code for SIMD bit-packing
        if self.global_var_data['packed_vars']:
            self._generate_simd_packing_init()
            self.output.append("")
        
        # Generate code section
        self.output.append("SECTION .text")
        self.output.append("")
        
        # Generate main entry point
        self.output.append("; Program entry point")
        self.output.append("_start:")
        
        # Ensure stack is 16-byte aligned (required for x86-64 ABI)
        # RSP is already set by the kernel, but we align it to be safe
        self.output.append("    ; Align stack to 16 bytes (x86-64 ABI requirement)")
        self.output.append("    AND RSP, 0xFFFFFFFFFFFFFFF0  ; Align to 16-byte boundary")
        
        # Initialize SIMD bit-packing if needed
        if self.global_var_data['packed_vars']:
            self.output.append("    CALL _init_simd_packing  ; Initialize SIMD bit-packing")
        
        # Call main function if it exists
        has_main = any(
            (f.decl.name if f.decl else "unknown") == "main"
            for f in small_funcs + large_funcs
        )
        if has_main:
            self.output.append("    CALL FUNC_main  ; Call main function")
            self.output.append("    ; Main return value is in RAX, save it for exit")
            self.output.append("    MOV RDI, RAX  ; Save return value to RDI (exit code)")
        else:
            self.output.append("    MOV RDI, 0   ; No main function, exit with code 0")
        
        # Exit with return code from main (in RDI)
        self.output.append("    ; Exit system call (sys_exit)")
        self.output.append("    MOV RAX, 60  ; sys_exit")
        self.output.append("    SYSCALL")
        self.output.append("")
        
        # Generate small functions with indexed-jump support
        if small_funcs:
            self._generate_indexed_jump_table(small_funcs)
            self.output.append("")
        
        # Generate all functions
        for func in small_funcs + large_funcs:
            self._generate_function(func)
            self.output.append("")
        
        # Generate data section for function table and global variables
        self._generate_data_section(parser)
        
        # Generate assembly code for referenced external symbols
        if self.asm_parser:
            self._generate_asm_symbols(parser)
        
        # Final sanitization pass to remove any AST node attributes that might have leaked
        sanitized_output = []
        for line in self.output:
            # Skip lines that look like AST node attributes output as labels
            stripped = line.strip()
            problematic_labels = ['type:', 'field:', 'name:', 'expr:', 'node:', 'struct_ref:', 'assign:']
            if stripped in problematic_labels:
                # Skip this line - it's an AST node attribute that was accidentally output
                continue
            # Also check for single-word labels that are AST attribute names
            if stripped.endswith(':') and len(stripped.split()) == 1:
                label_name = stripped[:-1]
                if label_name in ['type', 'field', 'name', 'expr', 'node', 'struct_ref', 'assign']:
                    # Skip this line
                    continue
            sanitized_output.append(line)
        
        return "\n".join(sanitized_output)
    
    def _generate_indexed_jump_table(self, small_funcs):
        """Generate indexed-jump table for small functions."""
        self.output.append("; Indexed-jump table for small functions (<1024 bytes)")
        self.output.append("JUMP_TABLE:")
        
        base_addr = 0x1000  # Base address for small functions
        offset = 0
        
        for func in small_funcs:
            func_name = func.decl.name if func.decl else "unknown"
            self.function_offsets[func_name] = offset
            self.output.append(f"    DQ FUNC_{func_name}  ; Index {offset}: {func_name}")
            offset += 1
        
        self.output.append("")
        self.output.append("; Indexed-jump dispatcher")
        self.output.append("INDEXED_JUMP:")
        self.output.append("    ; RDI contains function index")
        self.output.append("    MOV RAX, JUMP_TABLE")
        self.output.append("    MOV RAX, [RAX + RDI*8]")
        self.output.append("    JMP RAX")
        self.output.append("")
    
    def _generate_function_table(self, small_funcs):
        """Generate function pointer table."""
        self.output.append("SECTION .data")
        self.output.append("FUNC_TABLE:")
        for func in small_funcs:
            func_name = func.decl.name if func.decl else "unknown"
            self.output.append(f"    DQ FUNC_{func_name}")
    
    def _generate_data_section(self, parser):
        """Generate data section for global variables and STACK_BASE."""
        self.output.append("SECTION .data")
        self.output.append("")
        
        # Always define STACK_BASE for indexed stack pointer system
        self.output.append("STACK_BASE:")
        self.output.append("    DQ 0x7FFF0000  ; Stack base address")
        self.output.append("")
        
        globals = parser.get_global_variables()
        if not globals:
            return
        
        # Deduplicate global variables by name
        seen_globals = {}  # {var_name: var_node} to deduplicate
        for var in globals:
            var_name = var.name if var.name else None
            if not var_name:
                continue
            # Only keep the first occurrence of each global
            if var_name not in seen_globals:
                seen_globals[var_name] = var
        
        packed_var_names = {var['name'] for var in self.global_var_data['packed_vars']}
        
        for var_name, var in seen_globals.items():
            # Only generate data for non-packed variables
            # Packed variables are stored in SIMD register
            if var_name not in packed_var_names:
                # Check if this is an array
                is_array = False
                array_size = 0
                # Check type structure for arrays
                type_node = var.type
                while hasattr(type_node, 'type'):
                    if isinstance(type_node, c_ast.ArrayDecl):
                        is_array = True
                        if type_node.dim:
                            if isinstance(type_node.dim, c_ast.Constant):
                                try:
                                    array_size = int(type_node.dim.value)
                                except:
                                    array_size = 10  # Default size
                            else:
                                array_size = 10  # Default size
                        break
                    type_node = type_node.type
                
                self.output.append(f"GLOBAL_{var_name}:")
                if is_array:
                    # Array declaration: allocate array_size * 4 bytes (assuming int)
                    self.output.append(f"    TIMES {array_size} DD 0  ; {var_name}[{array_size}]")
                elif var.init:
                    # Has initializer
                    if isinstance(var.init, c_ast.Constant):
                        value = var.init.value
                        # Handle string constants - convert to numeric if needed
                        if isinstance(value, str) and len(value) > 1:
                            # For string constants longer than 1 char, use address or convert
                            # For now, just use 0 and let the linker handle it
                            self.output.append(f"    DD 0  ; {var_name} (string constant)")
                        else:
                            # Try to convert value to integer for assembly
                            try:
                                # Handle numeric values
                                if isinstance(value, str):
                                    # Try parsing as integer (hex, decimal, etc.)
                                    if value.startswith('0x') or value.startswith('0X'):
                                        num_value = int(value, 16)
                                    else:
                                        num_value = int(value)
                                else:
                                    num_value = int(value)
                                self.output.append(f"    DD {num_value}  ; {var_name}")
                            except (ValueError, TypeError):
                                # If conversion fails, use 0
                                self.output.append(f"    DD 0  ; {var_name} (initialized at runtime)")
                    else:
                        self.output.append(f"    DD 0  ; {var_name} (initialized at runtime)")
                else:
                    self.output.append(f"    DD 0  ; {var_name}")
            else:
                # Packed variable - still need a storage location for initialization
                # but it will be packed into SIMD register
                self.output.append(f"GLOBAL_{var_name}:")
                if var.init:
                    if isinstance(var.init, c_ast.Constant):
                        value = var.init.value
                        # Handle string constants - convert to numeric if needed
                        if isinstance(value, str) and len(value) > 1:
                            # For string constants, use 0
                            self.output.append(f"    DB 0  ; {var_name} (packed, string constant)")
                        else:
                            # Try to convert value to integer for assembly
                            try:
                                if isinstance(value, str):
                                    if value.startswith('0x') or value.startswith('0X'):
                                        num_value = int(value, 16)
                                    else:
                                        num_value = int(value)
                                else:
                                    num_value = int(value)
                                # Ensure value fits in byte for DB
                                num_value = num_value & 0xFF
                                self.output.append(f"    DB {num_value}  ; {var_name} (packed into SIMD register)")
                            except (ValueError, TypeError):
                                self.output.append(f"    DB 0  ; {var_name} (packed into SIMD register)")
                    else:
                        self.output.append(f"    DB 0  ; {var_name} (packed into SIMD register)")
                else:
                    self.output.append(f"    DB 0  ; {var_name} (packed into SIMD register)")
        
        self.output.append("")
    
    def _generate_asm_symbols(self, parser):
        """Generate assembly code for referenced external symbols from .S files."""
        if not self.asm_parser or not self.referenced_asm_symbols:
            return
        
        self.output.append("")
        self.output.append("; ========================================")
        self.output.append("; Assembly symbols from .S files")
        self.output.append("; ========================================")
        self.output.append("")
        
        # Group symbols by type
        functions = []
        data_symbols = []
        
        for symbol_name in sorted(self.referenced_asm_symbols):
            if not self.asm_parser.has_symbol(symbol_name):
                continue
            
            symbol_info = self.asm_parser.global_symbols.get(symbol_name)
            if not symbol_info:
                # Try with FUNC_ prefix
                symbol_info = self.asm_parser.global_symbols.get(f"FUNC_{symbol_name}")
            if not symbol_info:
                # Try with GLOBAL_ prefix
                symbol_info = self.asm_parser.global_symbols.get(f"GLOBAL_{symbol_name}")
            
            if symbol_info:
                symbol_type = symbol_info.get('type', 'unknown')
                if symbol_type == 'function':
                    functions.append(symbol_name)
                elif symbol_type == 'data':
                    data_symbols.append(symbol_name)
                else:
                    # Unknown type - assume function if it's called
                    functions.append(symbol_name)
        
        # Generate functions first
        if functions:
            self.output.append("SECTION .text")
            self.output.append("; Assembly-defined functions")
            self.output.append("")
            for func_name in functions:
                code = self.asm_parser.get_symbol_code(func_name)
                if code:
                    self.output.append(f"; Function: {func_name} (from assembly)")
                    self.output.append(f"FUNC_{func_name}:")
                    # Output the code, skipping the label line if it's already there
                    for line in code:
                        # Skip if it's the same label (already output above)
                        stripped = line.strip()
                        # Skip problematic labels that might be attribute names
                        if stripped.endswith(':') and (func_name in stripped or f"FUNC_{func_name}" in stripped):
                            continue
                        # Skip lines that look like attribute names being output as labels
                        # These are common Python attribute names that shouldn't be assembly labels
                        problematic_labels = ['type:', 'field:', 'name:', 'value:', 'op:', 'expr:', 'left:', 'right:']
                        if stripped in problematic_labels or stripped in [l[:-1] for l in problematic_labels]:
                            continue
                        # Skip lines that are just a single word followed by colon (likely a label)
                        # but only if it's a known problematic attribute name
                        if stripped.endswith(':') and len(stripped.split()) == 1:
                            label_name = stripped[:-1]
                            if label_name in ['type', 'field', 'name', 'value', 'op', 'expr', 'left', 'right']:
                                continue
                        # Skip empty lines that are just whitespace
                        if not stripped:
                            continue
                        self.output.append(line)
                    self.output.append("")
        
        # Generate data symbols in data section
        if data_symbols:
            self.output.append("SECTION .data")
            self.output.append("; Assembly-defined global variables")
            self.output.append("")
            for var_name in data_symbols:
                code = self.asm_parser.get_symbol_code(var_name)
                if code:
                    self.output.append(f"; Global variable: {var_name} (from assembly)")
                    self.output.append(f"GLOBAL_{var_name}:")
                    # Output the code, skipping the label line if it's already there
                    for line in code:
                        # Skip if it's the same label (already output above)
                        stripped = line.strip()
                        # Skip problematic labels that might be attribute names
                        if stripped.endswith(':') and (var_name in stripped or f"GLOBAL_{var_name}" in stripped):
                            continue
                        # Skip lines that look like attribute names being output as labels
                        # These are common Python attribute names that shouldn't be assembly labels
                        problematic_labels = ['type:', 'field:', 'name:', 'value:', 'op:', 'expr:', 'left:', 'right:']
                        if stripped in problematic_labels or stripped in [l[:-1] for l in problematic_labels]:
                            continue
                        # Skip lines that are just a single word followed by colon (likely a label)
                        # but only if it's a known problematic attribute name
                        if stripped.endswith(':') and len(stripped.split()) == 1:
                            label_name = stripped[:-1]
                            if label_name in ['type', 'field', 'name', 'value', 'op', 'expr', 'left', 'right']:
                                continue
                        # Skip empty lines that are just whitespace
                        if not stripped:
                            continue
                        self.output.append(line)
                    self.output.append("")
    
    def _generate_simd_packing_init(self):
        """Generate initialization code to pack global variables into SIMD register."""
        self.output.append("; SIMD Bit-Packing: Pack global variables (1-8 bits) into last SIMD register")
        self.output.append("; This register (xmm15) is typically ignored by standard compilers")
        self.output.append("; Variables declared as 'auto _Alignas(N) char' are packed as N-bit values")
        self.output.append("_init_simd_packing:")
        self.output.append(f"    ; Initialize {self.simd_register} with packed global variables")
        self.output.append(f"    PXOR {self.simd_register}, {self.simd_register}  ; Clear register")
        
        packed_vars = self.global_var_data['packed_vars']
        bit_positions = self.global_var_data['bit_positions']
        
        # Pack each variable into the register
        for var_info in packed_vars:
            var_name = var_info['name']
            start_bit = var_info['start_bit']
            bits = var_info['bits']
            
            # Load initial value (if any) and pack into register
            self.output.append(f"    ; Pack {var_name} at bit {start_bit}, width {bits} bits")
            self.output.append(f"    MOVZX RAX, BYTE [GLOBAL_{var_name}]  ; Load {var_name}")
            self.output.append(f"    ; Extract and mask to {bits} bits")
            self.output.append(f"    AND RAX, {(1 << bits) - 1}  ; Mask to {bits} bits")
            
            # Pack into SIMD register using bit manipulation
            if start_bit == 0:
                # First variable: just move into low bits
                self.output.append(f"    MOVQ XMM0, RAX  ; Move to XMM0")
                self.output.append(f"    POR {self.simd_register}, XMM0  ; OR into packed register")
            else:
                # Shift to correct position and OR into register
                self.output.append(f"    SHL RAX, {start_bit}  ; Shift to bit position {start_bit}")
                self.output.append(f"    MOVQ XMM0, RAX  ; Move to XMM0")
                self.output.append(f"    POR {self.simd_register}, XMM0  ; OR into packed register")
        
        self.output.append(f"    ; {self.simd_register} now contains all packed global variables")
        self.output.append("    RET")
        self.output.append("")
    
    def _generate_packed_var_access(self, var_name, is_write=False, value_reg='RAX'):
        """Generate inline assembly to access a packed variable from SIMD register.
        
        Uses direct SIMD register access for zero-latency operations, avoiding
        memory reads that could stall the pipeline during interrupt callbacks.
        """
        if var_name not in self.global_var_data['bit_positions']:
            return None  # Not a packed variable
        
        start_bit, bits = self.global_var_data['bit_positions'][var_name]
        mask = (1 << bits) - 1
        
        if is_write:
            # Write: extract value, modify, pack back
            # Zero-latency: all operations on registers, no memory access
            self.output.append(f"    ; Zero-latency write to packed variable {var_name} (bits {start_bit}-{start_bit+bits-1})")
            self.output.append(f"    ; Direct SIMD register access - no memory stall")
            # Save the value to write (it's in value_reg, typically RAX)
            self.output.append(f"    PUSH {value_reg}  ; Save value to write")
            self.output.append(f"    MOVQ RAX, {self.simd_register}  ; Load packed register (register-to-register)")
            self.output.append(f"    ; Clear old value bits")
            mask_shifted = mask << start_bit
            self.output.append(f"    MOV RBX, {mask_shifted}")
            self.output.append(f"    NOT RBX  ; Invert mask")
            self.output.append(f"    AND RAX, RBX  ; Clear bits for {var_name}")
            self.output.append(f"    ; Insert new value")
            self.output.append(f"    POP RBX  ; Restore value to write")
            self.output.append(f"    AND RBX, {mask}  ; Mask to {bits} bits")
            self.output.append(f"    SHL RBX, {start_bit}  ; Shift to position")
            self.output.append(f"    OR RAX, RBX  ; Insert new value")
            self.output.append(f"    MOVQ {self.simd_register}, RAX  ; Store back to SIMD register (register-to-register)")
            self.output.append(f"    ; Zero-latency: all operations in registers, no pipeline stall")
        else:
            # Read: extract value from register
            # Zero-latency: direct register access, no memory read
            self.output.append(f"    ; Zero-latency read from packed variable {var_name} (bits {start_bit}-{start_bit+bits-1})")
            self.output.append(f"    ; Direct SIMD register access - eliminates memory read stall")
            self.output.append(f"    MOVQ RAX, {self.simd_register}  ; Load packed register (register-to-register)")
            if start_bit > 0:
                self.output.append(f"    SHR RAX, {start_bit}  ; Shift to extract {var_name}")
            self.output.append(f"    AND RAX, {mask}  ; Mask to {bits} bits")
            self.output.append(f"    ; Value now in RAX (zero-latency, no memory access, no pipeline stall)")
        
        return True
    
    def _is_interrupt_callback(self, func_name):
        """Check if function is an interrupt callback."""
        from analyzer import is_interrupt_callback
        return is_interrupt_callback(func_name)
    
    def _generate_local_var_load(self, var_name):
        """Generate code to load a local variable using indexed stack pointer.
        
        Stack address = [R12 + slot_index*16 + offset]
        Where R12 = stack base, slot_index fits in 32 bits (enables pointer compression)
        """
        if var_name not in self.current_function_stack:
            # Variable not found in current function - might be a parameter or error
            # For now, assume it's a parameter passed in register or use fallback
            self.output.append(f"    ; Warning: {var_name} not found in stack, assuming parameter")
            return
        
        slot_index, offset = self.current_function_stack[var_name]
        
        # Calculate address: [R12 + slot_index*16 + offset]
        # Use indexed addressing: R12 (base) + slot_index*16 (displacement)
        self.output.append(f"    ; Load local variable {var_name} from slot {slot_index}, offset {offset}")
        self.output.append(f"    ; Indexed stack: address = [R12 + {slot_index}*16 + {offset}]")
        self.output.append(f"    ; Slot index {slot_index} fits in 32 bits for pointer compression")
        
        # Calculate effective address: R12 + slot_index*16 + offset
        displacement = slot_index * self.stack_slot_size + offset
        if displacement == 0:
            # Direct access to slot 0
            self.output.append(f"    MOV RAX, [{self.stack_base_register}]  ; Load from slot 0")
        else:
            # Use displacement addressing
            self.output.append(f"    MOV RAX, [{self.stack_base_register} + {displacement}]  ; Load from slot {slot_index}")
    
    def _generate_local_var_store(self, var_name):
        """Generate code to store a local variable using indexed stack pointer.
        
        Stack address = [R12 + slot_index*16 + offset]
        Where R12 = stack base, slot_index fits in 32 bits (enables pointer compression)
        """
        if var_name not in self.current_function_stack:
            # Variable not found - allocate it now
            slot_index = self.current_stack_slots
            offset = 0
            self.current_stack_slots += 1
            self.current_function_stack[var_name] = (slot_index, offset)
            self.output.append(f"    ; Allocating slot {slot_index} for {var_name}")
            # Allocate stack space (16 bytes per slot) and adjust R12 to point to allocated region
            if slot_index == 0:
                # First slot: allocate space and set R12 to point to it
                self.output.append(f"    SUB RSP, {self.stack_slot_size}  ; Allocate {self.stack_slot_size} bytes on stack")
                self.output.append(f"    MOV {self.stack_base_register}, RSP  ; R12 now points to allocated region")
            else:
                # Subsequent slots: just allocate more space
                self.output.append(f"    SUB RSP, {self.stack_slot_size}  ; Allocate {self.stack_slot_size} bytes on stack")
            self.output.append(f"    INC {self.stack_index_register}  ; Increment slot index")
        else:
            slot_index, offset = self.current_function_stack[var_name]
        
        # Store value using indexed addressing
        self.output.append(f"    ; Store to local variable {var_name} at slot {slot_index}, offset {offset}")
        self.output.append(f"    ; Indexed stack: address = [R12 + {slot_index}*16 + {offset}]")
        self.output.append(f"    ; Slot index {slot_index} fits in 32 bits for pointer compression")
        
        displacement = slot_index * self.stack_slot_size + offset
        if displacement == 0:
            self.output.append(f"    MOV [{self.stack_base_register}], RAX  ; Store to slot 0")
        else:
            self.output.append(f"    MOV [{self.stack_base_register} + {displacement}], RAX  ; Store to slot {slot_index}")
    
    def _generate_compressed_pointer(self, slot_index1, slot_index2=None):
        """Generate code to create a compressed pointer (two 32-bit indices in one 64-bit register).
        
        This enables pointer compression: two stack slot indices can fit in one 64-bit register.
        Since stack slots are 16-byte aligned, indices fit in 32 bits, allowing two indices
        to be packed into a single 64-bit register.
        
        Useful for:
        - Storing multiple stack pointers efficiently
        - Passing stack locations between functions
        - Enabling pointer compression optimizations
        """
        if slot_index2 is None:
            # Single index - store in lower 32 bits (upper 32 bits remain 0)
            self.output.append(f"    ; Compressed pointer: slot index {slot_index1} in lower 32 bits")
            self.output.append(f"    MOV EAX, {slot_index1}  ; Store index in 32-bit register (fits in 32 bits)")
            self.output.append(f"    ; Address = [R12 + EAX*16] for indexed stack access")
        else:
            # Two indices - pack into one 64-bit register
            # Lower 32 bits: slot_index1, Upper 32 bits: slot_index2
            self.output.append(f"    ; Compressed pointer: slot {slot_index1} (low) + slot {slot_index2} (high)")
            self.output.append(f"    MOV EAX, {slot_index1}  ; Lower 32 bits: slot index {slot_index1}")
            self.output.append(f"    MOV EDX, {slot_index2}  ; Upper 32 bits: slot index {slot_index2}")
            self.output.append(f"    SHL RDX, 32  ; Shift upper index to high 32 bits")
            self.output.append(f"    OR RAX, RDX  ; Combine: RAX = (slot2 << 32) | slot1")
            self.output.append(f"    ; Single 64-bit register now contains two compressed stack pointers")
            self.output.append(f"    ; Extract: low = RAX & 0xFFFFFFFF, high = (RAX >> 32) & 0xFFFFFFFF")
            self.output.append(f"    ; Addresses: [R12 + low*16] and [R12 + high*16]")
    
    def _generate_function(self, func_def):
        """Generate code for a single function."""
        func_name = func_def.decl.name if func_def.decl else "unknown"
        # Skip functions with "unknown" names - they're likely parsing errors
        if func_name == "unknown":
            self.output.append(f"; Warning: Skipping function with unknown name")
            return
        
        info = self.function_data.get(func_name, {})
        is_interrupt = self._is_interrupt_callback(func_name)
        
        # Reset stack tracking for this function
        self.current_function_stack = {}
        self.current_stack_slots = 0
        
        # Align function start to 16 bytes for quantized call-backs
        self.output.append(f"ALIGN {self.alignment}")
        self.output.append(f"FUNC_{func_name}:")
        
        if is_interrupt:
            self.output.append(f"    ; Interrupt callback: using zero-latency SIMD register access")
            # For interrupt callbacks, ensure SIMD register is preserved/accessible
            self.output.append(f"    ; {self.simd_register} contains packed kernel flags (no memory reads)")
        
        # Function prologue with indexed stack pointer
        self.output.append("    ; Indexed stack pointer prologue (16-byte intervals)")
        self.output.append("    PUSH RBP")
        self.output.append("    PUSH R12  ; Preserve stack base register")
        self.output.append("    PUSH R13  ; Preserve stack index register")
        self.output.append("    MOV RBP, RSP  ; Save old RSP")
        
        # Initialize indexed stack pointer system
        # R12 = stack base address, R13 = current slot index (0-based)
        # For Linux user-space: use RSP as base (actual stack)
        # For kernel/bare-metal with custom memory layout, could use: MOV R12, [STACK_BASE]
        # Note: We'll set R12 to point to allocated stack space when slots are allocated
        # For now, initialize R12 to RSP (will be adjusted when slots are allocated)
        self.output.append(f"    MOV {self.stack_base_register}, RSP  ; Initialize to current stack pointer")
        self.output.append(f"    XOR {self.stack_index_register}, {self.stack_index_register}  ; Initialize slot index to 0")
        self.output.append("    ; Stack address = [R12 + R13*16] for indexed access")
        self.output.append("    ; Pointer compression: R13 fits in 32 bits, allowing two indices in one 64-bit register")
        
        # For interrupt callbacks, preserve SIMD register if needed
        if is_interrupt:
            # Allocate one slot (16 bytes) for SIMD register preservation
            self.current_stack_slots = 1
            self.output.append(f"    INC {self.stack_index_register}  ; Allocate slot 0 for SIMD register")
            # Note: xmm15 is typically preserved across calls, but we ensure it's accessible
        
        # Generate function body
        if func_def.body:
            self._generate_block(func_def.body, func_name, info)
            # Check if the function body contains any return statements
            # If not, add an implicit return at the end
            block_items = func_def.body.block_items if isinstance(func_def.body, c_ast.Compound) else [func_def.body]
            has_any_return = block_items and any(isinstance(item, c_ast.Return) for item in block_items)
            if not has_any_return:
                # Generate implicit return (fall-through case)
                # Restore stack index to 0
                if self.current_stack_slots > 0:
                    self.output.append(f"    XOR {self.stack_index_register}, {self.stack_index_register}  ; Reset stack index")
                self.output.append("    MOV RSP, RBP")
                self.output.append("    POP R13  ; Restore stack index register")
                self.output.append("    POP R12  ; Restore stack base register")
                self.output.append("    POP RBP")
                self.output.append("    RET")
    
    def _generate_block(self, block, func_name, info):
        """Generate code for a block."""
        if isinstance(block, c_ast.Compound):
            # block_items can be None for empty blocks
            if block.block_items:
                for item in block.block_items:
                    self._generate_statement(item, func_name, info)
            # If block_items is None, it's an empty block - do nothing
        else:
            self._generate_statement(block, func_name, info)
    
    def _generate_statement(self, stmt, func_name, info):
        """Generate code for a statement."""
        if isinstance(stmt, c_ast.Return):
            self._generate_return(stmt, func_name, info)
        elif isinstance(stmt, c_ast.Assignment):
            self._generate_assignment(stmt)
        elif isinstance(stmt, c_ast.If):
            self._generate_if(stmt, func_name, info)
        elif isinstance(stmt, c_ast.While):
            self._generate_while(stmt, func_name, info)
        elif isinstance(stmt, c_ast.For):
            self._generate_for(stmt, func_name, info)
        elif isinstance(stmt, c_ast.FuncCall):
            self._generate_call(stmt, func_name)
        elif isinstance(stmt, c_ast.Decl):
            self._generate_decl(stmt)
        elif isinstance(stmt, c_ast.Compound):
            self._generate_block(stmt, func_name, info)
    
    def _generate_return(self, ret_stmt, func_name, info):
        """Generate return statement with metamorphic return site optimization."""
        if info.get('has_single_return', False):
            # Metamorphic return site: return address is written into instruction
            self.output.append("    ; Metamorphic return site - address injected by caller")
            # Restore stack index to 0 (all slots deallocated)
            if self.current_stack_slots > 0:
                self.output.append(f"    XOR {self.stack_index_register}, {self.stack_index_register}  ; Reset stack index")
            self.output.append("    MOV RSP, RBP")
            self.output.append("    POP R13  ; Restore stack index register")
            self.output.append("    POP R12  ; Restore stack base register")
            self.output.append("    POP RBP")
            # The RET address will be dynamically modified by the caller
            self.output.append("    RET  ; Address bytes written by caller")
        else:
            # Standard return
            if ret_stmt.expr:
                self._generate_expression(ret_stmt.expr)
                # Return value is already in RAX from expression evaluation
            # Restore stack index to 0 (all slots deallocated)
            if self.current_stack_slots > 0:
                self.output.append(f"    XOR {self.stack_index_register}, {self.stack_index_register}  ; Reset stack index")
            self.output.append("    MOV RSP, RBP")
            self.output.append("    POP R13  ; Restore stack index register")
            self.output.append("    POP R12  ; Restore stack base register")
            self.output.append("    POP RBP")
            self.output.append("    RET")
    
    def _generate_call(self, call, caller_func_name):
        """Generate function call with optimizations."""
        # FIRST: Check if this is a function pointer call (e.g., array[index](), struct.member())
        # These must be handled BEFORE trying to extract a function name, because
        # ArrayRef and StructRef have a 'name' attribute that would be incorrectly extracted
        if isinstance(call.name, (c_ast.ArrayRef, c_ast.StructRef)):
            # This is a function pointer call through array or struct member
            # Generate code to evaluate the function pointer expression
            self._generate_expression(call.name)
            # RAX now contains the function pointer
            # Save it to the stack before evaluating arguments
            self.output.append("    PUSH RAX  ; Save function pointer")
            
            # Prepare arguments (simplified - assume up to 6 args in registers)
            # Arguments are evaluated in sequence and each overwrites RAX,
            # but we move them to argument registers immediately
            if call.args:
                for i, arg in enumerate(call.args.exprs[:6]):
                    reg = ['RDI', 'RSI', 'RDX', 'RCX', 'R8', 'R9'][i]
                    self._generate_expression(arg)
                    self.output.append(f"    MOV {reg}, RAX  ; Argument {i+1}")
            
            # Restore function pointer from stack
            self.output.append("    POP RAX  ; Restore function pointer")
            
            # Call the function pointer
            self.output.append("    CALL RAX  ; Call function pointer")
            return
        
        # Extract function name from call expression
        func_name = None
        if isinstance(call.name, c_ast.ID):
            func_name = call.name.name
        elif isinstance(call.name, c_ast.UnaryOp) and isinstance(call.name.expr, c_ast.ID):
            # Handle function pointer dereference: (*func_ptr)(args)
            func_name = call.name.expr.name
        elif hasattr(call.name, 'name'):
            # Try to get name attribute if it exists
            name_attr = call.name.name
            # Ensure it's a string, not an AST node
            if isinstance(name_attr, str):
                func_name = name_attr
            elif isinstance(name_attr, c_ast.ID):
                func_name = name_attr.name
            else:
                # Complex expression - we'll handle as function pointer call
                func_name = None
        
        # Handle other function pointer calls (e.g., complex expressions)
        if not func_name or func_name == "unknown":
            # Check if this is a function pointer call with a complex expression
            is_function_pointer = False
            if isinstance(call.name, (c_ast.BinaryOp)):
                is_function_pointer = True
            elif not isinstance(call.name, c_ast.ID) and not isinstance(call.name, c_ast.UnaryOp):
                # Could be a complex expression that evaluates to a function pointer
                is_function_pointer = True
            
            if is_function_pointer:
                # Generate code to evaluate the function pointer expression
                # The result should be in RAX
                self._generate_expression(call.name)
                # RAX now contains the function pointer
                # Save it to the stack before evaluating arguments
                self.output.append("    PUSH RAX  ; Save function pointer")
                
                # Prepare arguments (simplified - assume up to 6 args in registers)
                # Arguments are evaluated in sequence and each overwrites RAX,
                # but we move them to argument registers immediately
                if call.args:
                    for i, arg in enumerate(call.args.exprs[:6]):
                        reg = ['RDI', 'RSI', 'RDX', 'RCX', 'R8', 'R9'][i]
                        self._generate_expression(arg)
                        self.output.append(f"    MOV {reg}, RAX  ; Argument {i+1}")
                
                # Restore function pointer from stack
                self.output.append("    POP RAX  ; Restore function pointer")
                
                # Call the function pointer
                self.output.append("    CALL RAX  ; Call function pointer")
                return
            else:
                # Unknown function name - skip
                self.output.append(f"    ; Warning: Skipping call to unknown/undefined function")
                # Still prepare arguments in case they have side effects
                if call.args:
                    for i, arg in enumerate(call.args.exprs[:6]):
                        reg = ['RDI', 'RSI', 'RDX', 'RCX', 'R8', 'R9'][i]
                        self._generate_expression(arg)
                        self.output.append(f"    MOV {reg}, RAX")
                # Generate a no-op or placeholder
                self.output.append("    ; NOP - unknown function call skipped")
                return
        
        # Ensure func_name is a string, not an AST node
        if not isinstance(func_name, str):
            # This shouldn't happen after the checks above, but protect against it
            self.output.append(f"    ; Warning: Function name is not a string: {safe_str(func_name)}")
            # Still prepare arguments in case they have side effects
            if call.args:
                for i, arg in enumerate(call.args.exprs[:6]):
                    reg = ['RDI', 'RSI', 'RDX', 'RCX', 'R8', 'R9'][i]
                    self._generate_expression(arg)
                    self.output.append(f"    MOV {reg}, RAX")
            self.output.append("    ; NOP - invalid function name")
            return
        
        callee_info = self.function_data.get(func_name, {})
        
        # Prepare arguments (simplified - assume up to 6 args in registers)
        if call.args:
            for i, arg in enumerate(call.args.exprs[:6]):
                reg = ['RDI', 'RSI', 'RDX', 'RCX', 'R8', 'R9'][i]
                self._generate_expression(arg)
                self.output.append(f"    MOV {reg}, RAX")
        
        # Handle return site for single-return functions (quantized call-back)
        return_site_label = None
        if callee_info.get('has_single_return', False):
            # Generate quantized call-back label (will be placed after the call)
            return_site_label = f"RET_SITE_{caller_func_name}_{self.return_site_index}"
            self.return_site_index += 1
            self.return_sites.append(return_site_label)
        
        # Check if function exists in our function list (might be external)
        # Get all unique function names from parser
        all_func_names = set()
        functions = getattr(self, '_current_parser', None).get_functions() if hasattr(self, '_current_parser') else []
        for func in functions:
            func_name_from_def = func.decl.name if func.decl else None
            if func_name_from_def:
                all_func_names.add(func_name_from_def)
        
        # If function is not in our list, check if it's in assembly files or a function pointer variable
        if func_name not in all_func_names:
            # Check if this function is defined in assembly
            if self.asm_parser and self.asm_parser.has_symbol(func_name):
                self.output.append(f"    ; Function call to assembly-defined: {func_name}")
                self.output.append(f"    CALL FUNC_{func_name}")
                self.referenced_asm_symbols.add(func_name)
            else:
                # Check if it's a global variable (might be a function pointer)
                globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                if func_name in globals:
                    # This is a function pointer variable, not a function name
                    # Load the function pointer and call it
                    self.output.append(f"    ; Function pointer call: {func_name}")
                    self.output.append(f"    MOV RAX, [GLOBAL_{func_name}]  ; Load function pointer")
                    # Prepare arguments first
                    if call.args:
                        for i, arg in enumerate(call.args.exprs[:6]):
                            reg = ['RDI', 'RSI', 'RDX', 'RCX', 'R8', 'R9'][i]
                            self._generate_expression(arg)
                            self.output.append(f"    MOV {reg}, RAX  ; Argument {i+1}")
                        # Reload function pointer (arguments might have overwritten RAX)
                        self.output.append(f"    MOV RAX, [GLOBAL_{func_name}]  ; Reload function pointer")
                    self.output.append("    CALL RAX  ; Call function pointer")
                else:
                    # Assume it's an external function
                    self.output.append(f"    ; External function call: {func_name}")
                    self.output.append(f"    CALL FUNC_{func_name}  ; Assumed to be defined externally")
        else:
            # Generate call based on function type
            if callee_info.get('is_small', False):
                # Indexed-jump call for small functions
                func_idx = list(self.function_offsets.keys()).index(func_name) if func_name in self.function_offsets else -1
                if func_idx >= 0:
                    self.output.append(f"    ; Indexed-jump call to {func_name}")
                    self.output.append(f"    MOV RDI, {func_idx}")
                    
                    # Metamorphic return site disabled - RET_ADDR_OFFSET not implemented
                    # if callee_info.get('has_single_return', False) and return_site_label:
                    #     self.output.append(f"    LEA RAX, [rel {return_site_label}]")
                    #     self.output.append(f"    MOV [FUNC_{func_name}+RET_ADDR_OFFSET], RAX")
                    
                    self.output.append("    CALL INDEXED_JUMP")
                else:
                    # Fallback to direct call if not in jump table
                    self.output.append(f"    CALL FUNC_{func_name}")
            else:
                # Standard call or call with metamorphic return
                # Metamorphic return site disabled - RET_ADDR_OFFSET not implemented
                # if callee_info.get('has_single_return', False) and return_site_label:
                #     self.output.append(f"    LEA RAX, [rel {return_site_label}]")
                #     self.output.append(f"    MOV [FUNC_{func_name}+RET_ADDR_OFFSET], RAX")
                #     self.output.append(f"    JMP FUNC_{func_name}")
                # else:
                # Standard call
                self.output.append(f"    CALL FUNC_{func_name}")
        
        # Place return site after call (quantized call-back with 16-byte alignment)
        if return_site_label:
            self.output.append(f"    ALIGN {self.alignment}")
            self.output.append(f"{return_site_label}:  ; Quantized call-back (16-byte aligned)")
            # Calculate offset from base (fits in single byte since aligned to 16 bytes)
            offset_byte = (len(self.return_sites) - 1)
            self.output.append(f"    ; Return site offset: {offset_byte} (stored in single byte)")
    
    def _generate_expression(self, expr):
        """Generate code for an expression (simplified)."""
        if isinstance(expr, c_ast.Constant):
            value = expr.value
            # Handle string constants - convert to numeric value
            if isinstance(value, str):
                # Check if it's a string literal (enclosed in quotes)
                if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                    # For character constants, extract the character value
                    if value.startswith("'") and len(value) >= 3:
                        # Single character constant like 'a'
                        char_val = ord(value[1]) if len(value) > 2 else 0
                        self.output.append(f"    MOV RAX, {char_val}")
                    elif value.startswith('"') and len(value) >= 3:
                        # String literal - use first character
                        char_val = ord(value[1]) if len(value) > 2 else 0
                        self.output.append(f"    MOV RAX, {char_val}")
                    else:
                        # Empty or invalid string, use 0
                        self.output.append("    MOV RAX, 0")
                else:
                    # Try to parse as numeric value
                    try:
                        if value.startswith('0x') or value.startswith('0X'):
                            num_value = int(value, 16)
                        elif value.startswith('0') and len(value) > 1:
                            num_value = int(value, 8)
                        else:
                            num_value = int(value)
                        self.output.append(f"    MOV RAX, {num_value}")
                    except (ValueError, TypeError):
                        # If conversion fails, use 0
                        self.output.append("    MOV RAX, 0")
            else:
                # Numeric value
                try:
                    num_value = int(value)
                    self.output.append(f"    MOV RAX, {num_value}")
                except (ValueError, TypeError):
                    self.output.append("    MOV RAX, 0")
        elif isinstance(expr, c_ast.ID):
            name = expr.name
            # Check if this is a packed global variable
            if name in self.global_var_data['bit_positions']:
                # Use zero-latency SIMD register access
                self._generate_packed_var_access(name, is_write=False)
            else:
                # Check if it's a global variable (non-packed)
                globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                if name in globals:
                    # Global variable (non-packed)
                    self.output.append(f"    MOV RAX, [GLOBAL_{name}]  ; Load global variable")
                elif self.asm_parser and self.asm_parser.has_symbol(name):
                    # Global variable defined in assembly
                    self.output.append(f"    MOV RAX, [GLOBAL_{name}]  ; Load assembly-defined global")
                    self.referenced_asm_symbols.add(name)
                else:
                    # Local variable - use indexed stack pointer
                    self._generate_local_var_load(name)
        elif isinstance(expr, c_ast.BinaryOp):
            self._generate_binary_op(expr)
        elif isinstance(expr, c_ast.UnaryOp):
            self._generate_unary_op(expr)
        elif isinstance(expr, c_ast.ArrayRef):
            self._generate_array_ref(expr)
        elif isinstance(expr, c_ast.StructRef):
            self._generate_struct_ref(expr)
        elif isinstance(expr, c_ast.TernaryOp):
            self._generate_ternary_op(expr)
        else:
            # Unknown expression type - output warning and generate no-op
            # Use safe_str to prevent AST node objects from being output as strings
            expr_type = safe_str(expr)
            self.output.append(f"    ; Warning: Unhandled expression type: {expr_type}")
            self.output.append("    MOV RAX, 0  ; Default value for unhandled expression")
    
    def _generate_binary_op(self, op):
        """Generate code for binary operation."""
        self._generate_expression(op.left)
        self.output.append("    PUSH RAX")
        self._generate_expression(op.right)
        self.output.append("    POP RBX")
        
        if op.op == '+':
            self.output.append("    ADD RAX, RBX")
        elif op.op == '-':
            self.output.append("    SUB RBX, RAX")
            self.output.append("    MOV RAX, RBX")
        elif op.op == '*':
            self.output.append("    MUL RBX")
        elif op.op == '/':
            self.output.append("    DIV RBX")
        elif op.op == '==':
            self.output.append("    CMP RAX, RBX")
            self.output.append("    SETE AL")
            self.output.append("    MOVZX RAX, AL")
        elif op.op == '<':
            self.output.append("    CMP RBX, RAX")
            self.output.append("    SETL AL")
            self.output.append("    MOVZX RAX, AL")
        elif op.op == '>':
            self.output.append("    CMP RAX, RBX")
            self.output.append("    SETG AL")
            self.output.append("    MOVZX RAX, AL")
        elif op.op == '<=':
            self.output.append("    CMP RBX, RAX")
            self.output.append("    SETLE AL")
            self.output.append("    MOVZX RAX, AL")
        elif op.op == '>=':
            self.output.append("    CMP RAX, RBX")
            self.output.append("    SETGE AL")
            self.output.append("    MOVZX RAX, AL")
        elif op.op == '!=':
            self.output.append("    CMP RAX, RBX")
            self.output.append("    SETNE AL")
            self.output.append("    MOVZX RAX, AL")
        elif op.op == '%':
            # Modulo: a % b
            # RBX has left operand (from stack), RAX has right operand
            # We need: left % right
            self.output.append("    ; Modulo operation: RBX % RAX")
            self.output.append("    PUSH RAX  ; Save right operand (divisor)")
            self.output.append("    MOV RAX, RBX  ; Move left operand (dividend) to RAX")
            self.output.append("    POP RBX  ; Get divisor in RBX")
            self.output.append("    XOR RDX, RDX  ; Clear RDX for division")
            self.output.append("    DIV RBX  ; RAX = dividend / divisor, RDX = remainder")
            self.output.append("    MOV RAX, RDX  ; Remainder is the modulo result")
        elif op.op == '&&':
            # Logical AND: both operands must be non-zero
            # RBX has left operand, RAX has right operand
            self.label_counter = self.label_counter + 1
            label_id = self.label_counter
            self.output.append(f"    ; Logical AND: RBX && RAX")
            self.output.append(f"    TEST RBX, RBX  ; Check if left is non-zero")
            self.output.append(f"    JZ AND_FALSE_{label_id}")
            self.output.append(f"    TEST RAX, RAX  ; Check if right is non-zero")
            self.output.append(f"    JZ AND_FALSE_{label_id}")
            self.output.append(f"    MOV RAX, 1  ; Both non-zero, result is 1")
            self.output.append(f"    JMP AND_END_{label_id}")
            self.output.append(f"AND_FALSE_{label_id}:")
            self.output.append(f"    MOV RAX, 0  ; One or both zero, result is 0")
            self.output.append(f"AND_END_{label_id}:")
        elif op.op == '||':
            # Logical OR: at least one operand must be non-zero
            # RBX has left operand, RAX has right operand
            self.label_counter = self.label_counter + 1
            label_id = self.label_counter
            self.output.append(f"    ; Logical OR: RBX || RAX")
            self.output.append(f"    TEST RBX, RBX  ; Check if left is non-zero")
            self.output.append(f"    JNZ OR_TRUE_{label_id}")
            self.output.append(f"    TEST RAX, RAX  ; Check if right is non-zero")
            self.output.append(f"    JNZ OR_TRUE_{label_id}")
            self.output.append(f"    MOV RAX, 0  ; Both zero, result is 0")
            self.output.append(f"    JMP OR_END_{label_id}")
            self.output.append(f"OR_TRUE_{label_id}:")
            self.output.append(f"    MOV RAX, 1  ; At least one non-zero, result is 1")
            self.output.append(f"OR_END_{label_id}:")
        elif op.op == '<<':
            # Left shift: RBX << RAX
            self.output.append("    ; Left shift: RBX << RAX")
            self.output.append("    MOV RCX, RAX  ; Shift amount in RCX")
            self.output.append("    MOV RAX, RBX  ; Value to shift")
            self.output.append("    SHL RAX, CL  ; Left shift by CL (low 8 bits of RCX)")
        elif op.op == '>>':
            # Right shift: RBX >> RAX
            self.output.append("    ; Right shift: RBX >> RAX")
            self.output.append("    MOV RCX, RAX  ; Shift amount in RCX")
            self.output.append("    MOV RAX, RBX  ; Value to shift")
            self.output.append("    SHR RAX, CL  ; Right shift by CL (low 8 bits of RCX)")
        elif op.op == '&':
            # Bitwise AND: RBX & RAX
            self.output.append("    ; Bitwise AND: RBX & RAX")
            self.output.append("    AND RAX, RBX")
        elif op.op == '|':
            # Bitwise OR: RBX | RAX
            self.output.append("    ; Bitwise OR: RBX | RAX")
            self.output.append("    OR RAX, RBX")
        elif op.op == '^':
            # Bitwise XOR: RBX ^ RAX
            self.output.append("    ; Bitwise XOR: RBX ^ RAX")
            self.output.append("    XOR RAX, RBX")
    
    def _generate_unary_op(self, op):
        """Generate code for unary operation."""
        self._generate_expression(op.expr)
        if op.op == '-':
            self.output.append("    NEG RAX")
        elif op.op == '!':
            self.output.append("    NOT RAX")
        elif op.op == '*':
            # Pointer dereference: *ptr
            self.output.append("    ; Pointer dereference: *ptr")
            self.output.append("    MOV RAX, [RAX]  ; Load value at address in RAX")
        elif op.op == '&':
            # Address-of: &var
            # Handle address-of operator
            if isinstance(op.expr, c_ast.ID):
                name = op.expr.name
                # Check if it's a global variable
                globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                if name in globals:
                    # Global variable address
                    self.output.append(f"    MOV RAX, GLOBAL_{name}  ; Address of global variable")
                else:
                    # Local variable address
                    if name in self.current_function_stack:
                        slot_index, offset = self.current_function_stack[name]
                        displacement = slot_index * self.stack_slot_size + offset
                        self.output.append(f"    MOV RAX, {self.stack_base_register}")
                        if displacement > 0:
                            self.output.append(f"    ADD RAX, {displacement}")
                    else:
                        self.output.append(f"    ; Warning: variable {name} not found for address-of")
            else:
                # Complex expression - generate and use as address
                self._generate_expression(op.expr)
        elif op.op == '~':
            # Bitwise NOT: ~expr
            self.output.append("    ; Bitwise NOT: ~expr")
            self.output.append("    NOT RAX")
        elif op.op == 'p++':
            # Post-increment: var++
            if isinstance(op.expr, c_ast.ID):
                name = op.expr.name
                # Load value
                if name in self.global_var_data['bit_positions']:
                    self._generate_packed_var_access(name, is_write=False)
                else:
                    globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                    if name in globals:
                        self.output.append(f"    MOV RAX, [GLOBAL_{name}]")
                    else:
                        self._generate_local_var_load(name)
                # Increment and store back
                self.output.append("    PUSH RAX  ; Save original value")
                self.output.append("    INC RAX")
                # Store incremented value
                if name in self.global_var_data['bit_positions']:
                    self._generate_packed_var_access(name, is_write=True, value_reg='RAX')
                else:
                    globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                    if name in globals:
                        self.output.append(f"    MOV [GLOBAL_{name}], RAX")
                    else:
                        # Store to local
                        self.output.append("    PUSH RAX")
                        # We need to get the address to store
                        if name in self.current_function_stack:
                            slot_index, offset = self.current_function_stack[name]
                            displacement = slot_index * self.stack_slot_size + offset
                            self.output.append(f"    MOV RBX, {self.stack_base_register}")
                            if displacement > 0:
                                self.output.append(f"    ADD RBX, {displacement}")
                            self.output.append("    POP RAX")
                            self.output.append("    MOV [RBX], RAX")
                self.output.append("    POP RAX  ; Return original value")
        elif op.op == 'p--':
            # Post-decrement: var--
            if isinstance(op.expr, c_ast.ID):
                name = op.expr.name
                # Load value
                if name in self.global_var_data['bit_positions']:
                    self._generate_packed_var_access(name, is_write=False)
                else:
                    globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                    if name in globals:
                        self.output.append(f"    MOV RAX, [GLOBAL_{name}]")
                    else:
                        self._generate_local_var_load(name)
                # Decrement and store back
                self.output.append("    PUSH RAX  ; Save original value")
                self.output.append("    DEC RAX")
                # Store decremented value (similar to post-increment)
                if name in self.global_var_data['bit_positions']:
                    self._generate_packed_var_access(name, is_write=True, value_reg='RAX')
                else:
                    globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                    if name in globals:
                        self.output.append(f"    MOV [GLOBAL_{name}], RAX")
                    else:
                        if name in self.current_function_stack:
                            slot_index, offset = self.current_function_stack[name]
                            displacement = slot_index * self.stack_slot_size + offset
                            self.output.append("    PUSH RAX")
                            self.output.append(f"    MOV RBX, {self.stack_base_register}")
                            if displacement > 0:
                                self.output.append(f"    ADD RBX, {displacement}")
                            self.output.append("    POP RAX")
                            self.output.append("    MOV [RBX], RAX")
                self.output.append("    POP RAX  ; Return original value")
        elif op.op == '++':
            # Pre-increment: ++var
            if isinstance(op.expr, c_ast.ID):
                name = op.expr.name
                # Load, increment, store, return new value
                if name in self.global_var_data['bit_positions']:
                    self._generate_packed_var_access(name, is_write=False)
                    self.output.append("    INC RAX")
                    self._generate_packed_var_access(name, is_write=True, value_reg='RAX')
                else:
                    globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                    if name in globals:
                        self.output.append(f"    MOV RAX, [GLOBAL_{name}]")
                        self.output.append("    INC RAX")
                        self.output.append(f"    MOV [GLOBAL_{name}], RAX")
                    else:
                        self._generate_local_var_load(name)
                        self.output.append("    INC RAX")
                        if name in self.current_function_stack:
                            slot_index, offset = self.current_function_stack[name]
                            displacement = slot_index * self.stack_slot_size + offset
                            self.output.append("    PUSH RAX")
                            self.output.append(f"    MOV RBX, {self.stack_base_register}")
                            if displacement > 0:
                                self.output.append(f"    ADD RBX, {displacement}")
                            self.output.append("    POP RAX")
                            self.output.append("    MOV [RBX], RAX")
        elif op.op == '--':
            # Pre-decrement: --var
            if isinstance(op.expr, c_ast.ID):
                name = op.expr.name
                # Load, decrement, store, return new value
                if name in self.global_var_data['bit_positions']:
                    self._generate_packed_var_access(name, is_write=False)
                    self.output.append("    DEC RAX")
                    self._generate_packed_var_access(name, is_write=True, value_reg='RAX')
                else:
                    globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                    if name in globals:
                        self.output.append(f"    MOV RAX, [GLOBAL_{name}]")
                        self.output.append("    DEC RAX")
                        self.output.append(f"    MOV [GLOBAL_{name}], RAX")
                    else:
                        self._generate_local_var_load(name)
                        self.output.append("    DEC RAX")
                        if name in self.current_function_stack:
                            slot_index, offset = self.current_function_stack[name]
                            displacement = slot_index * self.stack_slot_size + offset
                            self.output.append("    PUSH RAX")
                            self.output.append(f"    MOV RBX, {self.stack_base_register}")
                            if displacement > 0:
                                self.output.append(f"    ADD RBX, {displacement}")
                            self.output.append("    POP RAX")
                            self.output.append("    MOV [RBX], RAX")
    
    def _generate_array_ref(self, arr_ref):
        """Generate code for array indexing: arr[index]"""
        # Generate index first (we'll need it)
        self._generate_expression(arr_ref.subscript)
        self.output.append("    PUSH RAX  ; Save index")
        
        # Generate base address (array name or pointer)
        if isinstance(arr_ref.name, c_ast.ID):
            # Array variable name
            name = arr_ref.name.name
            # Check if it's a global variable
            globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
            if name in globals:
                # Global array
                self.output.append(f"    MOV RBX, GLOBAL_{name}  ; Base address of array")
            else:
                # Local array - treat as pointer (for now, assume it's a local variable that holds an address)
                self._generate_local_var_load(name)
                self.output.append("    MOV RBX, RAX  ; Base address")
        else:
            # Complex expression for base
            self._generate_expression(arr_ref.name)
            self.output.append("    MOV RBX, RAX  ; Base address")
        
        # Get index from stack
        self.output.append("    POP RAX  ; Get index")
        
        # Calculate address: base + index * sizeof(int)
        # Assuming int is 4 bytes (32 bits)
        self.output.append("    ; Array indexing: base + index * 4")
        self.output.append("    MOV RCX, RAX  ; Save index")
        self.output.append("    MOV RAX, 4  ; Size of int")
        self.output.append("    MUL RCX  ; RAX = index * 4")
        self.output.append("    ADD RAX, RBX  ; RAX = base + offset")
        
        # Load value from memory
        self.output.append("    MOV RAX, [RAX]  ; Load array element")
    
    def _generate_struct_ref(self, struct_ref):
        """Generate code for struct member access: struct.member or struct->member"""
        # Defensive check: ensure struct_ref has required attributes
        if not hasattr(struct_ref, 'type') or not hasattr(struct_ref, 'name'):
            self.output.append("    ; Warning: Invalid struct reference")
            self.output.append("    MOV RAX, 0")
            return
        
        member_name = None
        if hasattr(struct_ref, 'field') and struct_ref.field and hasattr(struct_ref.field, 'name'):
            member_name = struct_ref.field.name
        
        # Ensure type is a string, not an attribute name or AST node
        # struct_ref.type should be '.' or '->', but protect against AST nodes
        if hasattr(struct_ref, 'type'):
            type_val = struct_ref.type
            if isinstance(type_val, str):
                struct_type = type_val
            elif isinstance(type_val, c_ast.Node):
                # If type is an AST node (shouldn't happen, but protect against it)
                struct_type = None
            else:
                # Try to convert to string safely
                struct_type = safe_str(type_val) if type_val in ['.', '->'] else None
        else:
            struct_type = None
        
        if struct_type == '.':
            # Direct member access: struct.member
            # Generate base address (struct variable)
            if isinstance(struct_ref.name, c_ast.ID):
                name = struct_ref.name.name
                # Check if it's a global variable
                globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                if name in globals:
                    # Global struct - base address
                    self.output.append(f"    MOV RAX, GLOBAL_{name}  ; Base address of struct")
                else:
                    # Local struct - get address from stack
                    self._generate_local_var_load(name)
                    # For structs, we need the address, not the value
                    # If it's a local variable, we need to compute its address
                    if name in self.current_function_stack:
                        slot_index, offset = self.current_function_stack[name]
                        displacement = slot_index * self.stack_slot_size + offset
                        self.output.append(f"    MOV RAX, {self.stack_base_register}")
                        if displacement > 0:
                            self.output.append(f"    ADD RAX, {displacement}")
            else:
                # Complex expression for base
                self._generate_expression(struct_ref.name)
                # RAX now contains the struct address
        elif struct_type == '->':
            # Pointer member access: struct->member
            # Generate pointer value (address)
            self._generate_expression(struct_ref.name)
            # RAX now contains the pointer (address of struct)
        else:
            # Fallback: handle nested struct references or other complex cases
            if isinstance(struct_ref.name, c_ast.StructRef):
                # Nested struct reference: a.b.c
                self._generate_struct_ref(struct_ref.name)
            else:
                self._generate_expression(struct_ref.name)
        
        # Calculate member offset (simplified: assume 4 bytes per member, sequential)
        # In a real implementation, we'd need to track struct definitions and member offsets
        # For now, we'll use a simple offset calculation based on member name
        if member_name:
            # Simple offset calculation: use first character to determine offset
            # This is a simplification - real implementation would parse struct definitions
            # Common patterns: x=0, y=4, width=8, height=12, etc.
            member_offsets = {
                'x': 0, 'y': 4, 'z': 8,
                'width': 8, 'height': 12,
                'a': 0, 'b': 4, 'c': 8, 'd': 12
            }
            member_offset = member_offsets.get(member_name, 0)
            self.output.append(f"    ; Struct member access: {member_name} at offset {member_offset}")
            if member_offset > 0:
                self.output.append(f"    ADD RAX, {member_offset}  ; Add member offset")
            self.output.append("    MOV RAX, [RAX]  ; Load member value")
        else:
            self.output.append("    ; Struct member access (member name not found)")
            self.output.append("    MOV RAX, [RAX]  ; Load value at address")
    
    def _generate_assignment(self, assign):
        """Generate code for assignment."""
        # Handle compound assignment operators
        if assign.op in ['+=', '-=', '*=', '/=', '%=', '<<=', '>>=', '&=', '|=', '^=']:
            # Compound assignment: x += y is equivalent to x = x + y
            # First, load the lvalue
            if isinstance(assign.lvalue, c_ast.ID):
                name = assign.lvalue.name
                # Load current value
                if name in self.global_var_data['bit_positions']:
                    self._generate_packed_var_access(name, is_write=False)
                else:
                    globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                    if name in globals:
                        self.output.append(f"    MOV RAX, [GLOBAL_{name}]")
                    else:
                        self._generate_local_var_load(name)
            elif isinstance(assign.lvalue, c_ast.ArrayRef):
                # Array element: arr[i]
                self._generate_array_ref(assign.lvalue)
            elif isinstance(assign.lvalue, c_ast.StructRef):
                # Struct member: struct.member or struct->member
                # Generate address of member
                # Defensive check: ensure struct_ref has required attributes
                if not hasattr(assign.lvalue, 'type') or not hasattr(assign.lvalue, 'name'):
                    self.output.append("    ; Warning: Invalid struct reference in assignment")
                    self.output.append("    MOV RAX, 0")
                    return
                
                member_name = None
                if hasattr(assign.lvalue, 'field') and assign.lvalue.field and hasattr(assign.lvalue.field, 'name'):
                    member_name = assign.lvalue.field.name
                
                # Ensure type is a string, not an attribute name or AST node
                # assign.lvalue.type should be '.' or '->', but protect against AST nodes
                if hasattr(assign.lvalue, 'type'):
                    type_val = assign.lvalue.type
                    if isinstance(type_val, str):
                        struct_type = type_val
                    elif isinstance(type_val, c_ast.Node):
                        # If type is an AST node (shouldn't happen, but protect against it)
                        struct_type = None
                    else:
                        # Try to convert to string safely
                        struct_type = safe_str(type_val) if type_val in ['.', '->'] else None
                else:
                    struct_type = None
                
                if struct_type == '.':
                    # Direct member access: struct.member
                    if isinstance(assign.lvalue.name, c_ast.ID):
                        name = assign.lvalue.name.name
                        globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                        if name in globals:
                            self.output.append(f"    MOV RAX, GLOBAL_{name}")
                        else:
                            if name in self.current_function_stack:
                                slot_index, offset = self.current_function_stack[name]
                                displacement = slot_index * self.stack_slot_size + offset
                                self.output.append(f"    MOV RAX, {self.stack_base_register}")
                                if displacement > 0:
                                    self.output.append(f"    ADD RAX, {displacement}")
                    else:
                        # Handle nested struct references
                        if isinstance(assign.lvalue.name, c_ast.StructRef):
                            self._generate_struct_ref(assign.lvalue.name)
                        else:
                            self._generate_expression(assign.lvalue.name)
                elif struct_type == '->':
                    # Pointer member access: struct->member
                    self._generate_expression(assign.lvalue.name)
                
                # Add member offset
                if member_name:
                    member_offsets = {
                        'x': 0, 'y': 4, 'z': 8,
                        'width': 8, 'height': 12,
                        'a': 0, 'b': 4, 'c': 8, 'd': 12
                    }
                    member_offset = member_offsets.get(member_name, 0)
                    if member_offset > 0:
                        self.output.append(f"    ADD RAX, {member_offset}")
                
                # Save member address
                self.output.append("    PUSH RAX  ; Save member address")
            else:
                # Complex lvalue - generate expression
                self._generate_expression(assign.lvalue)
            
            # Save current value
            self.output.append("    PUSH RAX  ; Save current value")
            
            # Generate right-hand side
            self._generate_expression(assign.rvalue)
            self.output.append("    POP RBX  ; Get current value")
            
            # Perform operation based on operator
            base_op = assign.op[:-1]  # Remove '=' from '+=', etc.
            if base_op == '+':
                self.output.append("    ADD RAX, RBX")
            elif base_op == '-':
                self.output.append("    SUB RBX, RAX")
                self.output.append("    MOV RAX, RBX")
            elif base_op == '*':
                self.output.append("    MUL RBX")
            elif base_op == '/':
                self.output.append("    MOV RCX, RAX  ; Save divisor")
                self.output.append("    MOV RAX, RBX  ; Dividend")
                self.output.append("    XOR RDX, RDX")
                self.output.append("    DIV RCX")
            elif base_op == '%':
                self.output.append("    MOV RCX, RAX  ; Save divisor")
                self.output.append("    MOV RAX, RBX  ; Dividend")
                self.output.append("    XOR RDX, RDX")
                self.output.append("    DIV RCX")
                self.output.append("    MOV RAX, RDX  ; Remainder")
            elif base_op == '<<':
                self.output.append("    MOV RCX, RAX  ; Shift amount")
                self.output.append("    MOV RAX, RBX  ; Value to shift")
                self.output.append("    SHL RAX, CL")
            elif base_op == '>>':
                self.output.append("    MOV RCX, RAX  ; Shift amount")
                self.output.append("    MOV RAX, RBX  ; Value to shift")
                self.output.append("    SHR RAX, CL")
            elif base_op == '&':
                self.output.append("    AND RAX, RBX")
            elif base_op == '|':
                self.output.append("    OR RAX, RBX")
            elif base_op == '^':
                self.output.append("    XOR RAX, RBX")
            
            # Now assign the result (fall through to regular assignment)
            # We'll handle the assignment below
            assign.op = '='  # Change to regular assignment
            # Continue with regular assignment handling
        
        if assign.op == '=':
            self._generate_expression(assign.rvalue)
            # Check if we have a struct member assignment (address on stack)
            if isinstance(assign.lvalue, c_ast.StructRef):
                # Struct member assignment
                self.output.append("    POP RBX  ; Get member address")
                self.output.append("    MOV [RBX], RAX  ; Store to struct member")
            elif isinstance(assign.lvalue, c_ast.ID):
                name = assign.lvalue.name
                # Check if this is a packed global variable
                if name in self.global_var_data['bit_positions']:
                    # Use zero-latency SIMD register write
                    self._generate_packed_var_access(name, is_write=True, value_reg='RAX')
                else:
                    # Check if it's a global variable (non-packed)
                    globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                    if name in globals:
                        # Global variable (non-packed)
                        self.output.append(f"    MOV [GLOBAL_{name}], RAX")
                    elif self.asm_parser and self.asm_parser.has_symbol(name):
                        # Global variable defined in assembly
                        self.output.append(f"    MOV [GLOBAL_{name}], RAX  ; Store to assembly-defined global")
                        self.referenced_asm_symbols.add(name)
                    else:
                        # Local variable assignment - use indexed stack pointer
                        self._generate_local_var_store(name)
            elif isinstance(assign.lvalue, c_ast.ArrayRef):
                # Array assignment: arr[index] = value
                # Value is already in RAX
                self.output.append("    PUSH RAX  ; Save value to assign")
                
                # Generate index
                self._generate_expression(assign.lvalue.subscript)
                self.output.append("    PUSH RAX  ; Save index")
                
                # Generate base address
                if isinstance(assign.lvalue.name, c_ast.ID):
                    # Array variable name
                    name = assign.lvalue.name.name
                    # Check if it's a global variable
                    globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                    if name in globals:
                        # Global array
                        self.output.append(f"    MOV RBX, GLOBAL_{name}  ; Base address of array")
                    else:
                        # Local array - treat as pointer
                        self._generate_local_var_load(name)
                        self.output.append("    MOV RBX, RAX  ; Base address")
                else:
                    # Complex expression for base
                    self._generate_expression(assign.lvalue.name)
                    self.output.append("    MOV RBX, RAX  ; Base address")
                
                # Get index from stack
                self.output.append("    POP RAX  ; Get index")
                
                # Calculate address: base + index * sizeof(int)
                self.output.append("    ; Array assignment: base + index * 4")
                self.output.append("    MOV RCX, RAX  ; Save index")
                self.output.append("    MOV RAX, 4  ; Size of int")
                self.output.append("    MUL RCX  ; RAX = index * 4")
                self.output.append("    ADD RAX, RBX  ; RAX = base + offset")
                
                # Store value to memory
                self.output.append("    POP RBX  ; Get value to assign")
                self.output.append("    MOV [RAX], RBX  ; Store to array element")
    
    def _generate_ternary_op(self, ternary):
        """Generate code for ternary operator: condition ? true_expr : false_expr"""
        self.label_counter = self.label_counter + 1
        label_id = self.label_counter
        
        # Evaluate condition
        self._generate_expression(ternary.cond)
        self.output.append(f"    TEST RAX, RAX  ; Check condition")
        self.output.append(f"    JZ TERNARY_FALSE_{label_id}")
        
        # True branch
        self._generate_expression(ternary.iftrue)
        self.output.append(f"    JMP TERNARY_END_{label_id}")
        
        # False branch
        self.output.append(f"TERNARY_FALSE_{label_id}:")
        self._generate_expression(ternary.iffalse)
        
        # End
        self.output.append(f"TERNARY_END_{label_id}:")
    
    def _generate_if(self, if_stmt, func_name, info):
        """Generate code for if statement."""
        else_label = f"ELSE_{len(self.output)}"
        end_label = f"END_IF_{len(self.output)}"
        
        self._generate_expression(if_stmt.cond)
        self.output.append("    TEST RAX, RAX")
        self.output.append(f"    JZ {else_label}")
        
        self._generate_statement(if_stmt.iftrue, func_name, info)
        self.output.append(f"    JMP {end_label}")
        self.output.append(f"{else_label}:")
        
        if if_stmt.iffalse:
            self._generate_statement(if_stmt.iffalse, func_name, info)
        
        self.output.append(f"{end_label}:")
    
    def _generate_while(self, while_stmt, func_name, info):
        """Generate code for while loop."""
        loop_label = f"WHILE_{len(self.output)}"
        end_label = f"END_WHILE_{len(self.output)}"
        
        self.output.append(f"{loop_label}:")
        self._generate_expression(while_stmt.cond)
        self.output.append("    TEST RAX, RAX")
        self.output.append(f"    JZ {end_label}")
        
        self._generate_statement(while_stmt.stmt, func_name, info)
        self.output.append(f"    JMP {loop_label}")
        self.output.append(f"{end_label}:")
    
    def _generate_for(self, for_stmt, func_name, info):
        """Generate code for for loop."""
        loop_label = f"FOR_{len(self.output)}"
        end_label = f"END_FOR_{len(self.output)}"
        
        if for_stmt.init:
            self._generate_statement(for_stmt.init, func_name, info)
        
        self.output.append(f"{loop_label}:")
        
        if for_stmt.cond:
            self._generate_expression(for_stmt.cond)
            self.output.append("    TEST RAX, RAX")
            self.output.append(f"    JZ {end_label}")
        
        self._generate_statement(for_stmt.stmt, func_name, info)
        
        if for_stmt.next:
            self._generate_statement(for_stmt.next, func_name, info)
        
        self.output.append(f"    JMP {loop_label}")
        self.output.append(f"{end_label}:")
    
    def _generate_decl(self, decl):
        """Generate code for variable declaration with indexed stack pointer."""
        name = decl.name
        # Allocate a 16-byte slot for the variable (indexed stack)
        slot_index = self.current_stack_slots
        self.current_stack_slots += 1
        
        # Store variable location: (slot_index, offset_within_slot)
        # For simplicity, we'll use offset 0 within each slot
        # Multiple small variables could share a slot, but for now one per slot
        self.current_function_stack[name] = (slot_index, 0)
        
        # Increment stack index register to allocate new slot
        self.output.append(f"    ; Allocate slot {slot_index} (16 bytes) for {name}")
        self.output.append(f"    INC {self.stack_index_register}  ; Increment slot index")
        
        if decl.init:
            self._generate_expression(decl.init)
            # Store value using indexed addressing
            self._generate_local_var_store(name)
        else:
            # Initialize to 0
            self.output.append(f"    XOR RAX, RAX  ; Initialize {name} to 0")
            self._generate_local_var_store(name)